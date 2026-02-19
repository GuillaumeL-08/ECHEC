"""
ia_tree.py — IA d'échecs optimisée pour 10h d'entraînement en pur Python.

Optimisations clés :
  1. Table de transposition avec LRU (taille bornée) + flags exact/lower/upper
  2. Move ordering sans push/pop : MVV-LVA + killer moves + history heuristic
  3. Approfondissement itératif avec limite de temps
  4. Null-move pruning (élagage agressif en milieu de partie)
  5. Clé de Zobrist (entier 64-bit) au lieu de fen() string
  6. Évaluation incrémentale légère (matériel mis à jour hors minimax)
  7. Quiescence search pour éviter l'effet d'horizon sur les captures
  8. Learning : stocke uniquement (zobrist_key, score) → JSON compact
"""

from chess import (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, Board,
                   WHITE, BLACK, Move, BB_FILES, BB_RANKS, BB_ALL)
import random
import time
from collections import OrderedDict
from learning_manager import LearningManager

# ---------------------------------------------------------------------------
# Tables de pièces (Piece-Square Tables)
# ---------------------------------------------------------------------------
PIECE_VALUES = {PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 20000}

# ---------------------------------------------------------------------------
# Toutes les PST sont du point de vue des BLANCS (case 0=a1, 63=h8)
# Chaque rang est stocké de bas en haut : rang 1 en index 0..7, rang 8 en 56..63
# ---------------------------------------------------------------------------
PST = {
    # PION : avancement récompensé, centre valorisé, colonnes latérales pénalisées
    PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,  # rang 1 (pions ne peuvent pas être ici normalement)
        -5, -5, -5, -5, -5, -5, -5, -5,  # rang 2 (position de départ → légèrement négatif)
        -3,  0,  2,  5,  5,  2,  0, -3,  # rang 3
         0,  3,  8, 15, 15,  8,  3,  0,  # rang 4 (centre très valorisé)
         5,  8, 12, 20, 20, 12,  8,  5,  # rang 5 (avancé)
        15, 20, 28, 35, 35, 28, 20, 15,  # rang 6 (très avancé)
        40, 45, 50, 50, 50, 50, 45, 40,  # rang 7 (pré-promotion)
         0,  0,  0,  0,  0,  0,  0,  0,  # rang 8 (promotion)
    ],
    # CAVALIER : fort au centre, TRÈS pénalisé sur les bords (h4/a4 = pièce hors jeu)
    KNIGHT: [
        -80,-60,-40,-40,-40,-40,-60,-80,  # rang 1
        -60,-30,  0,  5,  5,  0,-30,-60,  # rang 2 : b1/g1 = position départ
        -40,  0, 15, 22, 22, 15,  0,-40,  # rang 3
        -40,  5, 22, 30, 30, 22,  5,-40,  # rang 4 : h4/a4 = -40 !
        -40,  5, 22, 30, 30, 22,  5,-40,  # rang 5
        -40,  0, 15, 22, 22, 15,  0,-40,  # rang 6
        -60,-30,  0,  0,  0,  0,-30,-60,  # rang 7
        -80,-60,-40,-40,-40,-40,-60,-80,  # rang 8
    ],
    # FOU : diagonales longues, éviter les bords
    BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  8,  0,  0,  0,  0,  8,-10,
        -10, 12, 12, 12, 12, 12, 12,-10,
        -10,  0, 12, 14, 14, 12,  0,-10,
        -10,  5,  8, 14, 14,  8,  5,-10,
        -10,  0,  8, 10, 10,  8,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    # TOUR : colonnes ouvertes (7e rang++) très importantes, 7e rang bonus fort
    ROOK: [
         0,  0,  0,  2,  2,  0,  0,  0,  # rang 1 : légèrement centré
        -5,  0,  0,  0,  0,  0,  0, -5,  # rang 2
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -3,  0,  0,  0,  0,  0,  0, -3,
        10, 15, 15, 15, 15, 15, 15, 10,  # rang 7 : très fort (tour sur 7e rang)
         5,  5,  8, 10, 10,  8,  5,  5,  # rang 8 : tour sur dernière rangée (finale)
    ],
    # DAME : milieu de partie — rester en arrière au début, actif au centre ensuite
    QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,  # rang 1
        -10,  0,  0,  0,  0,  0,  0,-10,  # rang 2
        -10,  0,  5,  5,  5,  5,  0,-10,  # rang 3
         -5,  0,  5,  8,  8,  5,  0, -5,  # rang 4
         -5,  0,  5,  8,  8,  5,  0, -5,  # rang 5
        -10,  0,  5,  5,  5,  5,  0,-10,  # rang 6
        -10,  0,  0,  0,  0,  0,  0,-10,  # rang 7
        -20,-10,-10, -5, -5,-10,-10,-20,  # rang 8
    ],
    # ROI milieu de partie : se cacher derrière les pions, roque encouragé
    KING: [
         20, 30, 10,  0,  0, 10, 30, 20,  # rang 1 : position après roque
         20, 20,  0,  0,  0,  0, 20, 20,  # rang 2 : derrière les pions
        -10,-20,-20,-20,-20,-20,-20,-10,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
    ],
}

# DAME en finale : plus active, doit s'approcher du roi adverse
QUEEN_ENDGAME = [
    -10, -5, -5, -5, -5, -5, -5,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
     -5,  5, 10, 10, 10, 10,  5, -5,
     -5,  5, 10, 15, 15, 10,  5, -5,
     -5,  5, 10, 15, 15, 10,  5, -5,
     -5,  5, 10, 10, 10, 10,  5, -5,
     -5,  0,  5,  5,  5,  5,  0, -5,
    -10, -5, -5, -5, -5, -5, -5,-10,
]

# TOUR en finale : colonnes ouvertes + couper le roi adverse
ROOK_ENDGAME = [
     0,  0,  5,  8,  8,  5,  0,  0,
     0,  5,  8, 10, 10,  8,  5,  0,
     0,  5,  8, 10, 10,  8,  5,  0,
     0,  5,  8, 10, 10,  8,  5,  0,
     0,  5,  8, 10, 10,  8,  5,  0,
     0,  5,  8, 10, 10,  8,  5,  0,
    10, 15, 15, 15, 15, 15, 15, 10,  # 7e rang toujours très fort
     5,  8, 10, 12, 12, 10,  8,  5,
]

# PION en finale : avancement crucial mais valeurs modérées (ne pas dépasser ~200 pts)
# pour ne jamais rentrer en compétition avec un score de mat (~99000)
PAWN_ENDGAME = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5,  5,  5,  5,  5,  5,  5,  5,  # rang 2
     8,  8, 10, 12, 12, 10,  8,  8,  # rang 3
    12, 14, 16, 20, 20, 16, 14, 12,  # rang 4
    20, 22, 25, 28, 28, 25, 22, 20,  # rang 5
    30, 33, 36, 40, 40, 36, 33, 30,  # rang 6
    45, 48, 50, 52, 52, 50, 48, 45,  # rang 7 (pré-promotion) — max 52, pas 70
     0,  0,  0,  0,  0,  0,  0,  0,  # rang 8 (promotion déjà comptée dans le matériel)
]

# ROI en finale : doit aller au centre pour aider les pions
KING_ENDGAME = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

# PST miroir pour les noirs : retourner la table (rang 8 devient rang 1)
PST_BLACK = {pt: list(reversed(table)) for pt, table in PST.items()}
PST_BLACK[KING] = list(reversed(PST[KING]))

# Tables de finale pour les noirs
QUEEN_ENDGAME_BLACK  = list(reversed(QUEEN_ENDGAME))
ROOK_ENDGAME_BLACK   = list(reversed(ROOK_ENDGAME))
PAWN_ENDGAME_BLACK   = list(reversed(PAWN_ENDGAME))
KING_ENDGAME_BLACK   = list(reversed(KING_ENDGAME))

# ---------------------------------------------------------------------------
# Livre d'ouvertures
# ---------------------------------------------------------------------------
OPENING_BOOK = {
    # ---- Position initiale ----
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1': [
        'e4', 'd4', 'c4', 'Nf3', 'g3', 'b3'
    ],

    # ---- Après 1.e4 ----
    'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1': [
        'e5', 'c5', 'e6', 'c6', 'd6', 'g6', 'd5'
    ],

    # ---- Après 1.d4 ----
    'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1': [
        'd5', 'Nf6', 'e6', 'f5', 'c5', 'g6'
    ],

    # ---- Après 1.c4 ----
    'rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1': [
        'e5', 'c5', 'Nf6', 'e6', 'g6', 'c6'
    ],

    # ---- Après 1.Nf3 ----
    'rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 0 1': [
        'd5', 'Nf6', 'c5', 'g6', 'e6'
    ],

    # ======================================================
    # Après 1.e4 e5
    # ======================================================
    'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'Nf3', 'Nc3', 'Bc4', 'f4', 'd4'
    ],
    # 1.e4 e5 2.Nf3
    'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 2': [
        'Nc6', 'Nf6', 'd6', 'f5'
    ],
    # 1.e4 e5 2.Nf3 Nc6 (Partie italienne / Espagnole)
    'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3': [
        'Bb5', 'Bc4', 'd4', 'Nc3'
    ],

    # ======================================================
    # Après 1.e4 c5 (Sicilienne)
    # ======================================================
    'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'Nf3', 'Nc3', 'd4', 'c3'
    ],
    # 1.e4 c5 2.Nf3
    'rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 2': [
        'd6', 'Nc6', 'e6', 'g6'
    ],

    # ======================================================
    # Après 1.e4 e6 (Française)
    # ======================================================
    'rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'd4', 'Nf3', 'Nc3', 'd3'
    ],
    # 1.e4 e6 2.d4
    'rnbqkbnr/pppp1ppp/4p3/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 2': [
        'd5', 'Nf6', 'c5', 'b6'
    ],

    # ======================================================
    # Après 1.e4 c6 (Caro-Kann)
    # ======================================================
    'rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'd4', 'Nf3', 'Nc3', 'd3'
    ],

    # ======================================================
    # Après 1.e4 d6 (Pirc)
    # ======================================================
    'rnbqkbnr/ppp1pppp/3p4/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'd4', 'Nf3', 'Nc3', 'f4'
    ],

    # ======================================================
    # Après 1.e4 d5 (Scandinave)
    # ======================================================
    'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'exd5', 'Nc3', 'e5'
    ],

    # ======================================================
    # Après 1.d4 d5
    # ======================================================
    'rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2': [
        'c4', 'Nf3', 'Nc3', 'Bf4', 'e3'
    ],
    # 1.d4 d5 2.c4 (Dame gambite)
    'rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2': [
        'e6', 'c6', 'dxc4', 'Nf6', 'e5'
    ],

    # ======================================================
    # Après 1.d4 Nf6
    # ======================================================
    'rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2': [
        'c4', 'Nf3', 'Bg5', 'e3', 'f3'
    ],
    # 1.d4 Nf6 2.c4 (Défense indienne)
    'rnbqkb1r/pppppppp/5n2/8/2PP4/8/PP2PPPP/RNBQKBNR b KQkq - 0 2': [
        'g6', 'e6', 'c5', 'd5', 'c6'
    ],

    # ======================================================
    # Après 1.d4 f5 (Hollandaise)
    # ======================================================
    'rnbqkbnr/ppppp1pp/8/5p2/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2': [
        'g3', 'Nf3', 'c4', 'Bg5', 'e3'
    ],
}

# ---------------------------------------------------------------------------
# LRU-bounded transposition table
# ---------------------------------------------------------------------------
class BoundedTT:
    """Table de transposition avec taille bornée (LRU eviction)."""
    EXACT, LOWER, UPPER = 0, 1, 2

    def __init__(self, max_size=500_000):
        self.max_size = max_size
        self._data = OrderedDict()

    def get(self, key):
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key, score, flag, depth, move):
        if key in self._data:
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self.max_size:
                self._data.popitem(last=False)  # evict LRU
        self._data[key] = (score, flag, depth, move)

    def clear(self):
        self._data.clear()

# ---------------------------------------------------------------------------
# Zobrist hashing simplifié
# ---------------------------------------------------------------------------
import random as _rng
_rng.seed(0xDEADBEEF)

_ZOBRIST_PIECE = {}
for _color in (True, False):
    for _pt in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING):
        for _sq in range(64):
            _ZOBRIST_PIECE[(_color, _pt, _sq)] = _rng.getrandbits(64)

_ZOBRIST_TURN = _rng.getrandbits(64)
_ZOBRIST_CASTLING = [_rng.getrandbits(64) for _ in range(16)]
_ZOBRIST_EP = [_rng.getrandbits(64) for _ in range(8)]

def zobrist_hash(board: Board) -> int:
    """Calcule un hash Zobrist 64-bit pour la position."""
    h = 0
    for sq in range(64):
        piece = board.piece_at(sq)
        if piece:
            h ^= _ZOBRIST_PIECE[(piece.color, piece.piece_type, sq)]
    if board.turn == WHITE:
        h ^= _ZOBRIST_TURN
    h ^= _ZOBRIST_CASTLING[board.castling_rights & 0xF]
    if board.ep_square is not None:
        h ^= _ZOBRIST_EP[board.ep_square % 8]
    return h


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------
class TreeIA:
    MAX_DEPTH = 10          # profondeur max pour l'approfondissement itératif
    TIME_LIMIT = 2.0        # secondes max par coup (ajustable)
    TT_SIZE = 400_000       # entrées max dans la table de transposition

    def __init__(self, depth=4, enable_learning=True, time_limit=2.0):
        self.depth = depth
        self.time_limit = time_limit
        self.board = None
        self.tt = BoundedTT(self.TT_SIZE)
        self.killer_moves = [[None, None] for _ in range(self.MAX_DEPTH + 2)]
        self.history = {}
        self.opening_moves_played = 0
        self.enable_learning = enable_learning
        self._start_time = 0.0
        self._nodes = 0
        self._piece_move_count = {}  # sq -> nb de fois que la pièce a bougé (opening)

        if enable_learning:
            self.learning_manager = LearningManager()
            self.learning_manager.start_new_game()
        else:
            self.learning_manager = None

    # ------------------------------------------------------------------
    # Évaluation statique
    # ------------------------------------------------------------------
    def _material_score(self) -> int:
        """Matériel pur, rapide."""
        score = 0
        for pt in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN):
            score += PIECE_VALUES[pt] * (
                len(self.board.pieces(pt, WHITE)) - len(self.board.pieces(pt, BLACK))
            )
        return score

    def _is_endgame(self) -> bool:
        queens = len(self.board.pieces(QUEEN, WHITE)) + len(self.board.pieces(QUEEN, BLACK))
        minors_w = len(self.board.pieces(KNIGHT, WHITE)) + len(self.board.pieces(BISHOP, WHITE))
        minors_b = len(self.board.pieces(KNIGHT, BLACK)) + len(self.board.pieces(BISHOP, BLACK))
        return queens == 0 or (queens == 2 and minors_w <= 1 and minors_b <= 1)

    def _king_distance(self, sq1: int, sq2: int) -> int:
        """Distance de Chebyshev entre deux cases (distance du roi aux échecs)."""
        r1, f1 = sq1 // 8, sq1 % 8
        r2, f2 = sq2 // 8, sq2 % 8
        return max(abs(r1 - r2), abs(f1 - f2))

    def _corner_distance(self, sq: int) -> int:
        """Distance du coin le plus proche (0=coin, 7=centre). Force le roi adverse au coin."""
        r, f = sq // 8, sq % 8
        return min(r, 7 - r) + min(f, 7 - f)

    def _is_winning_endgame(self, mat: int) -> int:
        """
        Retourne +1 si les blancs ont un avantage décisif, -1 si les noirs, 0 sinon.
        Utilisé pour activer l'heuristique de mat forcé.
        """
        if mat >= 500:   # avantage blanc d'au moins une tour
            return 1
        if mat <= -500:
            return -1
        return 0

    def _castling_score(self, wk, bk) -> int:
        """
        Bonus pour avoir roqué, pénalité pour avoir perdu le droit sans roquer.

        Détection du roque accompli :
        - Si le roi est en g1/c1 ET les droits de roque côté roi/dame sont perdus
          → il a forcément roqué (le roi ne peut pas aller en g1 autrement sans perdre les droits)
        - Si les droits sont perdus ET le roi n'est pas en position de roque → il a bougé sans roquer
        """
        score = 0
        b = self.board

        import chess as _chess

        # Droits actuels
        w_can_castle = b.has_castling_rights(WHITE)
        b_can_castle = b.has_castling_rights(BLACK)

        if wk is not None:
            w_castled_kingside  = (wk == 6  and not b.has_kingside_castling_rights(WHITE))
            w_castled_queenside = (wk == 2  and not b.has_queenside_castling_rights(WHITE))
            if w_castled_kingside or w_castled_queenside:
                score += 60   # a roqué → roi en sécurité
            elif not w_can_castle and wk not in (6, 2):
                score -= 50   # droits perdus sans roquer
            elif w_can_castle and wk == 4:
                score -= 10   # n'a pas encore roqué, légère pression

        if bk is not None:
            b_castled_kingside  = (bk == 62 and not b.has_kingside_castling_rights(BLACK))
            b_castled_queenside = (bk == 58 and not b.has_queenside_castling_rights(BLACK))
            if b_castled_kingside or b_castled_queenside:
                score -= 60
            elif not b_can_castle and bk not in (62, 58):
                score += 50
            elif b_can_castle and bk == 60:
                score += 10

        return score

    def _center_control_score(self) -> int:
        """
        Contrôle du centre pondéré par la phase de jeu.
        Symétrique : les bonus/malus sont identiques pour blancs et noirs.
        Le poids diminue avec le nombre de coups pour ne pas dominer le milieu de partie.
        """
        b = self.board
        ply = b.ply()

        if ply > 60:
            return 0

        # Poids décroissant : 1.0 au coup 0, 0 au coup 30
        weight = max(0.0, 1.0 - ply / 60.0)

        CENTER_STRICT   = [27, 28, 35, 36]   # d4, e4, d5, e5
        CENTER_EXTENDED = [18, 19, 20, 21,   # c3, d3, e3, f3
                           26, 29, 34, 37,   # c4, f4, c5, f5
                           42, 43, 44, 45]   # c6, d6, e6, f6

        score = 0

        for sq in CENTER_STRICT:
            piece = b.piece_at(sq)
            if piece:
                # Pion au centre vaut plus qu'une pièce (contrôle physique)
                val = 30 if piece.piece_type == PAWN else 15
                score += val if piece.color == WHITE else -val
            # Cases attaquées : symétrique, même valeur pour les deux camps
            w_attacks = b.is_attacked_by(WHITE, sq)
            b_attacks = b.is_attacked_by(BLACK, sq)
            if w_attacks and not b_attacks: score += 10   # contrôle exclusif blanc
            elif b_attacks and not w_attacks: score -= 10  # contrôle exclusif noir
            elif w_attacks and b_attacks: pass              # contesté → nul

        for sq in CENTER_EXTENDED:
            piece = b.piece_at(sq)
            if piece:
                val = 12 if piece.piece_type == PAWN else 6
                score += val if piece.color == WHITE else -val
            w_attacks = b.is_attacked_by(WHITE, sq)
            b_attacks = b.is_attacked_by(BLACK, sq)
            if w_attacks and not b_attacks: score += 3
            elif b_attacks and not w_attacks: score -= 3

        return int(score * weight)

    def _development_score(self) -> int:
        """
        Favorise le développement rapide en opening.
        """
        b = self.board
        ply = b.ply()

        if ply > 40:
            return 0

        weight = max(0.0, 1.0 - ply / 40.0)
        score = 0

        W_MINOR_START = {1: KNIGHT, 6: KNIGHT, 2: BISHOP, 5: BISHOP}
        B_MINOR_START = {57: KNIGHT, 62: KNIGHT, 58: BISHOP, 61: BISHOP}

        # 1) Pièces mineures non développées
        w_undeveloped = 0
        b_undeveloped = 0
        for sq, pt in W_MINOR_START.items():
            piece = b.piece_at(sq)
            if piece and piece.color == WHITE and piece.piece_type == pt:
                score -= 25
                w_undeveloped += 1
        for sq, pt in B_MINOR_START.items():
            piece = b.piece_at(sq)
            if piece and piece.color == BLACK and piece.piece_type == pt:
                score += 25
                b_undeveloped += 1

        # 2) Pénalité double mouvement — lecture directe du move stack
        # On sépare les coups blancs et noirs, et on vérifie si le dernier coup
        # d'un camp rebougé la même pièce que l'avant-dernier coup de ce camp.
        # C'est O(ply) mais ply <= 40 donc très rapide.
        if ply >= 4:
            moves = list(b.move_stack)
            white_moves = [m for i, m in enumerate(moves) if i % 2 == 0]
            black_moves = [m for i, m in enumerate(moves) if i % 2 == 1]

            def double_move_penalty(camp_moves, undeveloped, sign):
                pen = 0
                for j in range(1, len(camp_moves)):
                    prev, curr = camp_moves[j-1], camp_moves[j]
                    # Si la pièce qui vient d'arriver en prev.to_square est rebougée
                    if curr.from_square == prev.to_square and undeveloped >= 1:
                        # Vérifier que c'est bien une pièce mineure dans la position actuelle
                        piece = b.piece_at(curr.to_square)
                        if piece and piece.piece_type in (KNIGHT, BISHOP):
                            pen += sign * 40  # -40 blancs, +40 noirs
                return pen

            score += double_move_penalty(white_moves, w_undeveloped, -1)
            score += double_move_penalty(black_moves, b_undeveloped, +1)

        # 3) Dame sortie trop tôt
        if ply < 12:
            wq_sq = list(b.pieces(QUEEN, WHITE))
            bq_sq = list(b.pieces(QUEEN, BLACK))
            if wq_sq and wq_sq[0] != 3 and w_undeveloped >= 2:
                score -= 20 * w_undeveloped
            if bq_sq and bq_sq[0] != 59 and b_undeveloped >= 2:
                score += 20 * b_undeveloped

        # 4) Bonus développement
        for sq in b.pieces(KNIGHT, WHITE):
            if sq // 8 > 0:
                score += 10
        for sq in b.pieces(BISHOP, WHITE):
            if sq // 8 > 0:
                score += 8
        for sq in b.pieces(KNIGHT, BLACK):
            if sq // 8 < 7:
                score -= 10
        for sq in b.pieces(BISHOP, BLACK):
            if sq // 8 < 7:
                score -= 8

        return int(score * weight)

    def evaluate(self) -> int:
        """
        Retourne le score du point de vue du camp QUI JOUE (convention negamax).
        Positif = bon pour le camp qui joue, négatif = mauvais.
        """
        b = self.board
        if b.is_checkmate():
            depth_bonus = getattr(self, '_eval_depth', 0)
            return -99000 - depth_bonus  # toujours négatif : le camp qui joue est maté
        if b.is_stalemate() or b.is_insufficient_material() or b.is_seventyfive_moves():
            return 0

        # Score absolu (positif = blanc gagne)
        score = self._material_score()
        endgame = self._is_endgame()

        pawn_table_w = PAWN_ENDGAME       if endgame else PST[PAWN]
        pawn_table_b = PAWN_ENDGAME_BLACK if endgame else PST_BLACK[PAWN]
        for sq in b.pieces(PAWN, WHITE):
            score += pawn_table_w[sq]
        for sq in b.pieces(PAWN, BLACK):
            score -= pawn_table_b[sq]

        for pt in (KNIGHT, BISHOP):
            for sq in b.pieces(pt, WHITE):
                score += PST[pt][sq]
            for sq in b.pieces(pt, BLACK):
                score -= PST_BLACK[pt][sq]

        rook_table_w = ROOK_ENDGAME       if endgame else PST[ROOK]
        rook_table_b = ROOK_ENDGAME_BLACK if endgame else PST_BLACK[ROOK]
        for sq in b.pieces(ROOK, WHITE):
            score += rook_table_w[sq]
        for sq in b.pieces(ROOK, BLACK):
            score -= rook_table_b[sq]

        queen_table_w = QUEEN_ENDGAME       if endgame else PST[QUEEN]
        queen_table_b = QUEEN_ENDGAME_BLACK if endgame else PST_BLACK[QUEEN]
        for sq in b.pieces(QUEEN, WHITE):
            score += queen_table_w[sq]
        for sq in b.pieces(QUEEN, BLACK):
            score -= queen_table_b[sq]

        wk = b.king(WHITE)
        bk = b.king(BLACK)

        if endgame:
            if wk is not None: score += KING_ENDGAME[wk]
            if bk is not None: score -= KING_ENDGAME_BLACK[bk]
        else:
            if wk is not None: score += PST[KING][wk]
            if bk is not None: score -= PST_BLACK[KING][bk]

        if not endgame:
            score += self._development_score()
            score += self._castling_score(wk, bk)
            score += self._center_control_score()

        if endgame and not b.is_check():
            legal_moves = list(b.legal_moves)
            if len(legal_moves) <= 2:
                opp_has_moves = any(
                    b.piece_at(m.from_square) and b.piece_at(m.from_square).piece_type != KING
                    for m in legal_moves
                )
                if not opp_has_moves and len(legal_moves) > 0:
                    pat_penalty = -300 if b.turn == BLACK else 300
                    score += pat_penalty

        winning_side = self._is_winning_endgame(self._material_score())
        if winning_side != 0 and wk is not None and bk is not None:
            if winning_side == 1:
                enemy_corner = self._corner_distance(bk)
                score += (14 - enemy_corner) * 20
                kings_dist = self._king_distance(wk, bk)
                score += (7 - kings_dist) * 15
                enemy_king_moves = len([m for m in b.generate_pseudo_legal_moves(
                    b.occupied_co[BLACK]) if b.piece_at(m.from_square) and
                    b.piece_at(m.from_square).piece_type == KING])
                score += (8 - enemy_king_moves) * 10
            else:
                enemy_corner = self._corner_distance(wk)
                score -= (14 - enemy_corner) * 20
                kings_dist = self._king_distance(wk, bk)
                score -= (7 - kings_dist) * 15
                enemy_king_moves = len([m for m in b.generate_pseudo_legal_moves(
                    b.occupied_co[WHITE]) if b.piece_at(m.from_square) and
                    b.piece_at(m.from_square).piece_type == KING])
                score -= (8 - enemy_king_moves) * 10

        if len(b.pieces(BISHOP, WHITE)) >= 2: score += 30
        if len(b.pieces(BISHOP, BLACK)) >= 2: score -= 30

        score += self._pawn_structure_fast()
        score += self._mobility_score()

        if self.learning_manager:
            score = self.learning_manager.get_position_value_with_learning(b, score)

        # CONVENTION NEGAMAX : retourner du point de vue du camp qui joue
        return score if b.turn == WHITE else -score

    def _pawn_structure_fast(self) -> int:
        """Structure de pions via bitmasks de fichiers — beaucoup plus rapide que la boucle."""
        score = 0
        wp = self.board.pieces(PAWN, WHITE)
        bp = self.board.pieces(PAWN, BLACK)

        # Fichiers avec pions blancs / noirs
        w_files = set(sq % 8 for sq in wp)
        b_files = set(sq % 8 for sq in bp)

        # Pions doublés
        from collections import Counter
        wf_count = Counter(sq % 8 for sq in wp)
        bf_count = Counter(sq % 8 for sq in bp)
        for f, c in wf_count.items():
            if c > 1: score -= 20 * (c - 1)
        for f, c in bf_count.items():
            if c > 1: score += 20 * (c - 1)

        # Pions isolés
        for f in w_files:
            if (f-1) not in w_files and (f+1) not in w_files:
                score -= 15
        for f in b_files:
            if (f-1) not in b_files and (f+1) not in b_files:
                score += 15

        # Pions passés (approximatif via rank)
        for sq in wp:
            rank = sq // 8
            if not any(s // 8 > rank and s % 8 == sq % 8 for s in bp):
                score += 20 + rank * 8
        for sq in bp:
            rank = sq // 8
            if not any(s // 8 < rank and s % 8 == sq % 8 for s in wp):
                score -= 20 + (7 - rank) * 8

        return score

    def _mobility_score(self) -> int:
        """Mobilité légère sans générer tous les coups légaux."""
        # On approxime avec pseudo-légaux (beaucoup plus rapide)
        b = self.board
        w_mob = sum(1 for _ in b.generate_pseudo_legal_moves(b.occupied_co[WHITE]))
        b_mob = sum(1 for _ in b.generate_pseudo_legal_moves(b.occupied_co[BLACK]))
        return (w_mob - b_mob)

    # ------------------------------------------------------------------
    # Tri des coups (sans push/pop !)
    # ------------------------------------------------------------------
    def _move_score(self, move: Move, depth: int) -> int:
        """Score d'un coup pour le tri — SANS push/pop (rapide)."""
        score = 0
        b = self.board

        # 0) Pénalité forte pour les coups qui créent une répétition
        if self._is_repetition_move(move):
            score -= 500

        # 1) Captures : MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
        if b.is_capture(move):
            victim = b.piece_at(move.to_square)
            aggressor = b.piece_at(move.from_square)
            if victim and aggressor:
                score += 10 * PIECE_VALUES.get(victim.piece_type, 0) \
                            - PIECE_VALUES.get(aggressor.piece_type, 0)
            else:
                score += 500  # en passant

        # 2) Promotions
        if move.promotion:
            score += PIECE_VALUES.get(move.promotion, 0)

        # 3) Killer moves (coups calmes qui ont causé des coupures beta)
        ply = self.depth - depth
        if 0 <= ply < len(self.killer_moves):
            if move == self.killer_moves[ply][0]:
                score += 90
            elif move == self.killer_moves[ply][1]:
                score += 80

        # 4) History heuristic
        score += self.history.get((move.from_square, move.to_square), 0) // 256

        return score

    def _order_moves(self, moves, depth: int):
        scored = [(self._move_score(m, depth), m) for m in moves]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _update_killer(self, move: Move, depth: int):
        ply = self.depth - depth
        if 0 <= ply < len(self.killer_moves):
            if move != self.killer_moves[ply][0]:
                self.killer_moves[ply][1] = self.killer_moves[ply][0]
                self.killer_moves[ply][0] = move

    def _update_history(self, move: Move, depth: int):
        key = (move.from_square, move.to_square)
        self.history[key] = self.history.get(key, 0) + depth * depth
        # Limiter la croissance (aging)
        if len(self.history) > 8192:
            self.history = {k: v // 2 for k, v in self.history.items()}

    # ------------------------------------------------------------------
    # Quiescence search
    # ------------------------------------------------------------------
    def quiescence(self, alpha: int, beta: int, depth: int = 0) -> int:
        """Cherche uniquement les captures pour éviter l'effet d'horizon."""
        self._nodes += 1
        self._eval_depth = depth  # profondeur relative pour scorer les mats
        stand_pat = self.evaluate()

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Générer uniquement les captures
        captures = [m for m in self.board.legal_moves if self.board.is_capture(m)]
        captures = self._order_moves(captures, 0)

        for move in captures:
            # Delta pruning : si même en capturant la meilleure pièce on ne peut pas améliorer
            victim = self.board.piece_at(move.to_square)
            if victim and stand_pat + PIECE_VALUES.get(victim.piece_type, 0) + 200 < alpha:
                continue

            self.board.push(move)
            score = -self.quiescence(-beta, -alpha, depth - 1)
            self.board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    # ------------------------------------------------------------------
    # Minimax avec alpha-beta, TT, null-move, killers, history
    # ------------------------------------------------------------------
    def minimax(self, depth: int, alpha: int, beta: int, maximizing: bool) -> tuple:
        self._nodes += 1

        # Timeout check
        if self._nodes % 2048 == 0 and time.time() - self._start_time > self.time_limit:
            return None, None  # signal timeout

        b = self.board

        # Répétition AVANT la TT : la TT peut cacher une répétition mise en cache
        # is_repetition(2) = position vue 2 fois → jouer ce coup = 3ème = nulle forcée
        if b.is_repetition(2):
            mat = self._material_score()
            # Si on est en avantage, la répétition est une mauvaise issue → pénaliser
            if (maximizing and mat > 100) or (not maximizing and mat < -100):
                return -200, None
            return 0, None

        # TT lookup
        zkey = zobrist_hash(b)
        tt_entry = self.tt.get(zkey)
        tt_move = None
        if tt_entry:
            tt_score, tt_flag, tt_depth, tt_move = tt_entry
            if tt_depth >= depth:
                if tt_flag == BoundedTT.EXACT:
                    return tt_score, tt_move
                elif tt_flag == BoundedTT.LOWER:
                    alpha = max(alpha, tt_score)
                elif tt_flag == BoundedTT.UPPER:
                    beta = min(beta, tt_score)
                if alpha >= beta:
                    return tt_score, tt_move

        # Feuille
        if depth == 0 or b.is_game_over():
            self._eval_depth = depth  # transmis à evaluate() pour scorer les mats rapidement
            score = self.quiescence(alpha, beta, depth)
            return score, None

        # Null-move pruning (pas en fin de partie, pas en échec)
        R = 2  # réduction
        if (depth >= R + 1
                and not b.is_check()
                and not self._is_endgame()
                and abs(alpha) < 90000):
            b.push(Move.null())
            null_score, _ = self.minimax(depth - R - 1, -beta, -beta + 1, not maximizing)
            b.pop()
            if null_score is not None and -null_score >= beta:
                return beta, None

        # Générer et trier les coups (TT move en premier)
        legal = list(b.legal_moves)
        if not legal:
            return self.evaluate(), None

        # Mettre le coup TT en tête
        if tt_move and tt_move in legal:
            legal.remove(tt_move)
            legal.insert(0, tt_move)
        moves = self._order_moves(legal, depth)

        best_move = None
        original_alpha = alpha

        if maximizing:
            best_score = -10**9
            for i, move in enumerate(moves):
                b.push(move)
                # LMR : Late Move Reduction (coups tardifs cherchés moins profond)
                if i >= 4 and depth >= 3 and not b.is_check() and not b.is_capture(move):
                    score, _ = self.minimax(depth - 2, alpha, beta, False)
                    if score is not None and score > alpha:
                        score, _ = self.minimax(depth - 1, alpha, beta, False)
                else:
                    score, _ = self.minimax(depth - 1, alpha, beta, False)
                b.pop()

                if score is None:
                    return None, None  # timeout propagé

                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    if not self.board.is_capture(move):
                        self._update_killer(move, depth)
                        self._update_history(move, depth)
                    break

            flag = (BoundedTT.EXACT if original_alpha < best_score < beta
                    else BoundedTT.LOWER if best_score >= beta
                    else BoundedTT.UPPER)
            self.tt.put(zkey, best_score, flag, depth, best_move)
            return best_score, best_move

        else:
            best_score = 10**9
            for i, move in enumerate(moves):
                b.push(move)
                if i >= 4 and depth >= 3 and not b.is_check() and not b.is_capture(move):
                    score, _ = self.minimax(depth - 2, -beta, -alpha, True)
                    if score is not None and -score < beta:
                        score, _ = self.minimax(depth - 1, -beta, -alpha, True)
                    if score is not None:
                        score = score  # garder le score tel quel pour min
                else:
                    score, _ = self.minimax(depth - 1, -beta, -alpha, True)
                b.pop()

                if score is None:
                    return None, None

                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, best_score)
                if beta <= alpha:
                    if not self.board.is_capture(move):
                        self._update_killer(move, depth)
                        self._update_history(move, depth)
                    break

            flag = (BoundedTT.EXACT if original_alpha < best_score < beta
                    else BoundedTT.UPPER if best_score <= alpha
                    else BoundedTT.LOWER)
            self.tt.put(zkey, best_score, flag, depth, best_move)
            return best_score, best_move

    # ------------------------------------------------------------------
    # Approfondissement itératif (Iterative Deepening)
    # ------------------------------------------------------------------
    def _is_repetition_move(self, move: Move) -> bool:
        """Vérifie si jouer ce coup mène à une répétition de position."""
        self.board.push(move)
        is_rep = self.board.is_repetition(2)
        self.board.pop()
        return is_rep

    def iterative_deepening(self) -> Move:
        """Cherche de plus en plus profond jusqu'à la limite de temps."""
        self._start_time = time.time()
        self._nodes = 0
        maximizing = self.board.turn == WHITE

        best_move = None
        legal = list(self.board.legal_moves)
        if not legal:
            raise ValueError("Aucun coup légal disponible")

        # Fallback : préférer un coup qui ne crée pas de répétition
        non_repeating = [m for m in legal if not self._is_repetition_move(m)]
        best_move = non_repeating[0] if non_repeating else legal[0]

        for current_depth in range(1, self.MAX_DEPTH + 1):
            score, move = self.minimax(current_depth, -10**9, 10**9, maximizing)

            if score is None or move is None:
                break

            best_move = move
            elapsed = time.time() - self._start_time
            if elapsed > self.time_limit * 0.85:
                break

        return best_move

    # ------------------------------------------------------------------
    # Livre d'ouvertures
    # ------------------------------------------------------------------
    def get_opening_move(self, board: Board):
        fen = board.fen()
        if fen in OPENING_BOOK:
            for move_san in random.sample(OPENING_BOOK[fen], len(OPENING_BOOK[fen])):
                try:
                    move = board.push_san(move_san)
                    board.pop()
                    return board.san(move)
                except ValueError:
                    continue
        return None

    # ------------------------------------------------------------------
    # Interface publique
    # ------------------------------------------------------------------
    def coup(self, board: Board) -> str:
        self.board = board

        # Réinitialiser les killers entre les coups
        self.killer_moves = [[None, None] for _ in range(self.MAX_DEPTH + 2)]

        # Livre d'ouvertures
        if self.opening_moves_played < 12:
            opening_move = self.get_opening_move(board)
            if opening_move:
                self.opening_moves_played += 1
                return opening_move
            else:
                self.opening_moves_played = 12

        # Exploration aléatoire
        if self.learning_manager and self.learning_manager.should_explore():
            legal = list(board.legal_moves)
            if legal:
                non_rep = [m for m in legal if not self._is_repetition_move(m)]
                move = random.choice(non_rep if non_rep else legal)
                self._track_piece_move(board, move)
                if self.learning_manager:
                    self.learning_manager.record_move(board, move, self.evaluate())
                return board.san(move)

        # Recherche principale
        move = self.iterative_deepening()
        self._track_piece_move(board, move)

        if self.learning_manager:
            self.learning_manager.record_move(board, move, self.evaluate())

        return board.san(move)

    def _track_piece_move(self, board: Board, move: Move):
        """Met à jour le compteur de mouvements par pièce pour détecter les doubles mouvements."""
        if board.ply() > 40:
            return
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type in (KNIGHT, BISHOP):
            # Clé = case de destination (où la pièce sera après le coup)
            dest = move.to_square
            self._piece_move_count[dest] = self._piece_move_count.get(dest, 0) + 1
            # Supprimer l'ancienne case (la pièce n'y est plus)
            if move.from_square in self._piece_move_count:
                old_count = self._piece_move_count.pop(move.from_square)
                # Propager le count vers la nouvelle case
                self._piece_move_count[dest] = max(
                    self._piece_move_count[dest], old_count + 1
                )

    def end_game(self, result: str, board=None, color=None):
        """
        Réinitialise l'IA pour une nouvelle partie.
        - Depuis test_learning.py : learning_manager.end_game() est appelé directement
          avec la bonne couleur, donc ici on fait juste le reset.
        - Depuis canvas_tkinter.py (UI) : color doit être passé pour que l'apprentissage
          soit correct.
        """
        if self.learning_manager:
            final_board = board or getattr(self, 'board', None) or Board()
            if color is not None:
                # Appel depuis l'UI avec la couleur : gérer l'apprentissage ici
                self.learning_manager.end_game(result, final_board, color=color)
            # Dans tous les cas, préparer la prochaine partie
            self.learning_manager.start_new_game()
        self.opening_moves_played = 0
        self.tt.clear()
        self.history = {}
        self._piece_move_count = {}  # reset pour la nouvelle partie

    def get_learning_stats(self):
        if self.learning_manager:
            return self.learning_manager.get_learning_stats()
        return None