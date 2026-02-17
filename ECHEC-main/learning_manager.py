import json
import os
import random
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import chess
import chess.pgn

class LearningManager:
    """Gère l'apprentissage par renforcement de l'IA d'échecs."""
    
    def __init__(self, data_file: str = "ia_learning_data.json"):
        self.data_file = data_file
        self.position_values: Dict[str, float] = {}  # FEN -> valeur apprise
        self.move_history: List[Dict] = []  # Historique des parties
        self.current_game_moves: List[Tuple[str, str, float]] = []  # (FEN, move, score)
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        self.discount_factor = 0.9
        self.games_played = 0
        
        self.load_learning_data()
    
    def load_learning_data(self):
        """Charge les données d'apprentissage depuis le fichier JSON."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.position_values = data.get('position_values', {})
                    self.move_history = data.get('move_history', [])
                    self.games_played = data.get('games_played', 0)
                    print(f"Données d'apprentissage chargées: {len(self.position_values)} positions, {self.games_played} parties")
            except Exception as e:
                print(f"Erreur lors du chargement des données: {e}")
                self.position_values = {}
                self.move_history = []
                self.games_played = 0
    
    def save_learning_data(self):
        """Sauvegarde les données d'apprentissage dans le fichier JSON."""
        data = {
            'position_values': self.position_values,
            'move_history': self.move_history[-1000:],  # Garder seulement les 1000 dernières parties
            'games_played': self.games_played,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Données d'apprentissage sauvegardées: {len(self.position_values)} positions")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des données: {e}")
    
    def start_new_game(self):
        """Commence une nouvelle partie pour l'apprentissage."""
        self.current_game_moves = []
    
    def record_move(self, board: chess.Board, move: chess.Move, score: float):
        """Enregistre un coup joué avec son score d'évaluation."""
        fen = board.fen()
        move_str = board.san(move)
        self.current_game_moves.append((fen, move_str, score))
    
    def end_game(self, result: str, final_board: chess.Board):
        """Termine une partie et met à jour l'apprentissage."""
        self.games_played += 1
        
        # Calculer la récompense finale
        if result == "1-0":  # Blanc gagne
            final_reward = 1000.0
        elif result == "0-1":  # Noir gagne
            final_reward = -1000.0
        else:  # Nulle
            final_reward = 0.0
        
        # Mettre à jour les valeurs des positions avec rétropropagation
        self._update_position_values(final_reward)
        
        # Enregistrer la partie dans l'historique
        game_data = {
            'result': result,
            'moves': self.current_game_moves,
            'final_reward': final_reward,
            'timestamp': datetime.now().isoformat()
        }
        self.move_history.append(game_data)
        
        # Sauvegarder périodiquement
        if self.games_played % 10 == 0:
            self.save_learning_data()
    
    def _update_position_values(self, final_reward: float):
        """Met à jour les valeurs des positions par rétropropagation."""
        # Récompense inversée pour les noirs
        reward = final_reward
        
        # Parcourir les coups en ordre inverse pour la rétropropagation
        for i, (fen, move_str, score) in enumerate(reversed(self.current_game_moves)):
            # La récompense diminue avec le temps (discount factor)
            discounted_reward = reward * (self.discount_factor ** i)
            
            # Mettre à jour la valeur de la position
            if fen not in self.position_values:
                self.position_values[fen] = score
            
            # Apprentissage: ajuster la valeur en fonction du résultat
            old_value = self.position_values[fen]
            new_value = old_value + self.learning_rate * (discounted_reward - old_value)
            self.position_values[fen] = new_value
    
    def get_learned_position_value(self, fen: str) -> Optional[float]:
        """Retourne la valeur apprise pour une position donnée."""
        return self.position_values.get(fen)
    
    def get_position_value_with_learning(self, board: chess.Board, base_score: float) -> float:
        """Combine le score de base avec la valeur apprise."""
        fen = board.fen()
        learned_value = self.get_learned_position_value(fen)
        
        if learned_value is not None:
            # Pondérer entre le score de base et la valeur apprise
            weight = min(0.3, len(self.current_game_moves) * 0.01)  # Plus de confiance avec l'expérience
            return base_score * (1 - weight) + learned_value * weight
        
        return base_score
    
    def should_explore(self) -> bool:
        """Détermine si l'IA doit explorer (jouer un coup différent) ou exploiter."""
        # Moins d'exploration avec l'expérience
        adjusted_exploration = self.exploration_rate * (0.95 ** self.games_played)
        return random.random() < adjusted_exploration
    
    def get_learning_stats(self) -> Dict:
        """Retourne des statistiques sur l'apprentissage."""
        return {
            'games_played': self.games_played,
            'positions_learned': len(self.position_values),
            'recent_games': len(self.move_history),
            'exploration_rate': self.exploration_rate * (0.95 ** self.games_played)
        }
