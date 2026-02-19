import json
import os
import gzip
import random
import tempfile
from datetime import datetime
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional
import chess


class BoundedDict:
    """Dictionnaire LRU borné pour éviter la fuite mémoire après 10h."""

    def __init__(self, max_size: int = 200_000):
        self.max_size = max_size
        self._d = OrderedDict()

    def get(self, key, default=None):
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return default

    def __setitem__(self, key, value):
        if key in self._d:
            self._d.move_to_end(key)
        else:
            if len(self._d) >= self.max_size:
                self._d.popitem(last=False)
        self._d[key] = value

    def __contains__(self, key):
        return key in self._d

    def __len__(self):
        return len(self._d)

    def items(self):
        return self._d.items()

    def to_dict(self) -> dict:
        return dict(self._d)

    @classmethod
    def from_dict(cls, d: dict, max_size: int = 200_000):
        obj = cls(max_size)
        for k, v in list(d.items())[-max_size:]:
            obj._d[k] = v
        return obj


class LearningManager:
    """Apprentissage par renforcement optimisé pour 10h d'entraînement."""

    MAX_POSITIONS = 200_000
    LR = 0.15
    GAMMA = 0.92
    EXPLORE_START = 0.25
    EXPLORE_MIN = 0.02
    EXPLORE_DECAY = 0.997

    def __init__(self, data_file: str = "ia_learning_data.json"):
        # BUG FIX: nom de fichier par défaut .json simple (cohérent avec ia_tree.py)
        # Détecte automatiquement si un .gz ou .json existe déjà
        if data_file.endswith('.gz'):
            self.data_file = data_file
        elif os.path.exists(data_file + '.gz'):
            # Préfère le .gz s'il existe
            self.data_file = data_file + '.gz'
        else:
            self.data_file = data_file  # .json simple

        self.position_values: BoundedDict = BoundedDict(self.MAX_POSITIONS)
        self.current_game_moves: List[Tuple[int, str, float]] = []
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.exploration_rate = self.EXPLORE_START

        self._load()

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------
    def _load(self):
        paths_to_try = [self.data_file]
        # Essaie aussi l'autre format si disponible
        if self.data_file.endswith('.gz'):
            paths_to_try.append(self.data_file[:-3])
        else:
            paths_to_try.append(self.data_file + '.gz')

        for path in paths_to_try:
            if not os.path.exists(path):
                continue
            if os.path.getsize(path) == 0:
                print(f"[Learning] Fichier vide ignoré: {path}")
                os.remove(path)
                continue
            try:
                if path.endswith('.gz'):
                    with gzip.open(path, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    with open(path, 'r', encoding='utf-8') as f:
                        raw = f.read().strip()
                    # Protection contre du code collé après le JSON
                    brace_end = raw.rfind('}')
                    if brace_end == -1:
                        raise ValueError("Pas de JSON valide")
                    data = json.loads(raw[:brace_end + 1])

                raw_pos = data.get('position_values', {})
                bd = BoundedDict(self.MAX_POSITIONS)
                for k, v in list(raw_pos.items())[-self.MAX_POSITIONS:]:
                    bd._d[int(k)] = v
                self.position_values = bd

                self.games_played = data.get('games_played', 0)
                self.wins = data.get('wins', 0)
                self.losses = data.get('losses', 0)
                self.draws = data.get('draws', 0)
                self.exploration_rate = max(
                    self.EXPLORE_MIN,
                    self.EXPLORE_START * (self.EXPLORE_DECAY ** self.games_played)
                )
                print(f"[Learning] Chargé: {len(self.position_values)} positions, "
                      f"{self.games_played} parties "
                      f"(W:{self.wins} D:{self.draws} L:{self.losses})")
                return
            except Exception as e:
                print(f"[Learning] Erreur chargement {path}: {e} — réinitialisation.")
                try:
                    os.remove(path)
                except Exception:
                    pass

        print("[Learning] Démarrage à zéro.")

    def _save(self):
        data = {
            'position_values': {str(k): v for k, v in self.position_values.items()},
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'last_updated': datetime.now().isoformat(),
        }
        # Sauvegarde atomique : écrire dans tmp puis renommer
        tmp_path = self.data_file + '.tmp'
        try:
            if self.data_file.endswith('.gz'):
                with gzip.open(tmp_path, 'wt', encoding='utf-8', compresslevel=6) as f:
                    json.dump(data, f, separators=(',', ':'))
            else:
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.data_file)
            print(f"[Learning] Sauvegardé: {len(self.position_values)} positions, "
                  f"{self.games_played} parties.")
        except Exception as e:
            print(f"[Learning] Erreur sauvegarde: {e}")
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Interface jeu
    # ------------------------------------------------------------------
    def start_new_game(self):
        self.current_game_moves = []

    def record_move(self, board: chess.Board, move: chess.Move, score: float,
                    zobrist_key: Optional[int] = None):
        if zobrist_key is None:
            zobrist_key = hash(board.fen()) & 0xFFFFFFFFFFFFFFFF
        self.current_game_moves.append((zobrist_key, board.san(move), float(score)))

    def end_game(self, result: str, final_board: chess.Board, color: bool = chess.WHITE):
        """
        Met à jour l'apprentissage.
        color : chess.WHITE si cette IA joue les blancs, chess.BLACK si elle joue les noirs.
        Les stats W/D/L sont du point de vue de la couleur de l'IA.
        """
        self.games_played += 1

        # Résultat du point de vue de CETTE IA selon sa couleur
        if result == "1-0":
            final_reward = 1000.0 if color == chess.WHITE else -1000.0
            if color == chess.WHITE:
                self.wins += 1
            else:
                self.losses += 1
        elif result == "0-1":
            final_reward = -1000.0 if color == chess.WHITE else 1000.0
            if color == chess.WHITE:
                self.losses += 1
            else:
                self.wins += 1
        elif result == "1/2-1/2":
            final_reward = 0.0
            self.draws += 1
        else:
            # Partie interrompue (MAX_MOVES atteint, résultat "*") :
            # ne pas compter comme nulle, utiliser le matériel pour estimer
            mat = self._material_eval(final_board)
            if color == chess.BLACK:
                mat = -mat  # inverser pour les noirs
            if mat > 150:
                final_reward = 300.0   # légèrement positif
                self.wins += 1
            elif mat < -150:
                final_reward = -300.0
                self.losses += 1
            else:
                final_reward = 0.0
                self.draws += 1

        # Reward shaping : signal intermédiaire basé sur le matériel final
        mat = self._material_eval(final_board)
        shaped_reward = final_reward + mat * 0.1

        self._backpropagate(shaped_reward)

        # Décroissance de l'exploration
        self.exploration_rate = max(
            self.EXPLORE_MIN,
            self.exploration_rate * self.EXPLORE_DECAY
        )

        # BUG FIX: sauvegarder après CHAQUE partie (plus de condition % N)
        self._save()

    def _material_eval(self, board: chess.Board) -> float:
        VALS = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
                chess.ROOK: 500, chess.QUEEN: 900}
        score = 0.0
        for pt, val in VALS.items():
            score += val * (len(board.pieces(pt, chess.WHITE)) -
                            len(board.pieces(pt, chess.BLACK)))
        return score

    def _backpropagate(self, final_reward: float):
        for i, (zkey, _, base_score) in enumerate(reversed(self.current_game_moves)):
            discounted = final_reward * (self.GAMMA ** i)
            old = self.position_values.get(zkey, base_score)
            self.position_values[zkey] = old + self.LR * (discounted - old)

    # ------------------------------------------------------------------
    # Utilisation pendant la recherche
    # ------------------------------------------------------------------
    def get_position_value_with_learning(self, board: chess.Board, base_score: float,
                                          zobrist_key: Optional[int] = None) -> float:
        if zobrist_key is None:
            zobrist_key = hash(board.fen()) & 0xFFFFFFFFFFFFFFFF
        learned = self.position_values.get(zobrist_key)
        if learned is not None:
            weight = min(0.40, self.games_played * 0.002)
            return base_score * (1.0 - weight) + learned * weight
        return base_score

    def should_explore(self) -> bool:
        return random.random() < self.exploration_rate

    def get_learning_stats(self) -> dict:
        total = max(1, self.games_played)
        return {
            'games_played': self.games_played,
            'positions_learned': len(self.position_values),
            'wins': self.wins,
            'draws': self.draws,
            'losses': self.losses,
            'win_rate': round(self.wins / total, 3),
            'exploration_rate': round(self.exploration_rate, 4),
        }

    def force_save(self):
        """Forcer une sauvegarde immédiate (appeler à la fermeture)."""
        self._save()