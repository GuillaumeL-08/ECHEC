from chess import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from chess import WHITE
import random
OPENING_BOOK = {
    # Blancs
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1': [
        # Meilleures ouvertures pour les blancs
        'e4',    # Ouverture du Roi (meilleure statistiquement)
        'd4',    # Partie d'Avant
        'Nf3',   # Réti
    ],
    
    # Noirs - réponse à e4
    'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2': [
        'e5',    # Défense du Roi
        'c5',    # Défense Sicilienne
        'e6',    # Défense Française
        'c6',    # Défense Caro-Kann
    ],
    
    # Noirs - réponse à d4
    'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 2': [
        'd5',    # Défense du Gambit de Dame
        'Nf6',   # Défense Indienne
        'e6',    # Défense Française avancée
    ],
    
    # Lignes principales après 1.e4 e5
    'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2': [
        'Nf3',   # Développement standard
        'Bc4',   # Partie Italienne
        'Bb5',   # Partie Espagnole
    ],
    
    # Lignes après 1.e4 e5 2.Nf3
    'rnbqkb1r/pppp1ppp/2n2q2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 1 3': [
        'Bc4',   # Partie Italienne
        'Bb5',   # Partie Espagnole
        'd4',    # Partie Écossaise
    ],
    
    # Lignes après 1.e4 c5 (Sicilienne)
    'rnbqkb1r/pp1ppppp/2p4n/8/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 1 2': [
        'd4',    # Variante ouverte
        'Nf3',   # Variante principale
        'c3',    # Variante Alapine
    ],
}


PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

# Tables de position pour les pions (bonus/malus selon la position)
PAWN_TABLE_WHITE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    5, 10, 10,-20,-20, 10, 10,  5,
    5, -5,-10,  0,  0,-10, -5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5,  5, 10, 25, 25, 10,  5,  5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
    0,  0,  0,  0,  0,  0,  0,  0
]

PAWN_TABLE_BLACK = [x for x in reversed(PAWN_TABLE_WHITE)]

# Tables de position pour les cavaliers
KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]


class TreeIA:
    def __init__(self, depth=2):
        self.depth = depth
        self.transposition_table = {}  # Mémoire transposition
        self.opening_moves_played = 0  # Compteur pour savoir quand quitter le livre

    def evaluate(self) -> int:
        """Évaluation avancée de la position."""
        if self.board.is_checkmate():
            return -100000 if self.board.turn == WHITE else 100000
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            return 0

        score = 0
        
        # 1) Évaluation matérielle
        for piece_type in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN]:
            white_pieces = len(self.board.pieces(piece_type, WHITE))
            black_pieces = len(self.board.pieces(piece_type, not WHITE))
            score += PIECE_VALUES[piece_type] * (white_pieces - black_pieces)

        # 2) Évaluation positionnelle avancée
        
        # Pions - avec tables de position
        for square in self.board.pieces(PAWN, WHITE):
            score += PAWN_TABLE_WHITE[square]
            # Bonus pour pions passés
            if self._is_passed_pawn(square, WHITE):
                score += 50 + (square // 8) * 10
                
        for square in self.board.pieces(PAWN, not WHITE):
            score -= PAWN_TABLE_BLACK[square]
            # Malus pour pions passés adverses
            if self._is_passed_pawn(square, not WHITE):
                score -= 50 + (7 - square // 8) * 10

        # Structure des pions
        score += self._evaluate_pawn_structure()
        
        # 3) Évaluation des pièces avec tables de position
        for square in self.board.pieces(KNIGHT, WHITE):
            score += KNIGHT_TABLE[square]
        for square in self.board.pieces(KNIGHT, not WHITE):
            score -= KNIGHT_TABLE[63-square]  # Symétrie horizontale
            
        # 4) Contrôle du centre
        score += self._evaluate_center_control()
        
        # 5) Mobilité
        white_mobility = len(list(self.board.legal_moves)) if self.board.turn == WHITE else 0
        black_mobility = len(list(self.board.legal_moves)) if self.board.turn != WHITE else 0
        score += 2 * (white_mobility - black_mobility)
        
        # 6) Sécurité du roi
        score += self._evaluate_king_safety()
        
        return score

    def _is_passed_pawn(self, square, color):
        """Vérifie si un pion est passé."""
        file = square % 8
        # Vérifie s'il y a des pions adverses devant sur les files adjacentes
        for check_file in [file-1, file, file+1]:
            if 0 <= check_file <= 7:
                if color == WHITE:
                    # Pour les blancs, vérifie les rangées supérieures
                    for rank in range(square // 8 + 1, 8):
                        check_square = rank * 8 + check_file
                        if self.board.piece_at(check_square) == PAWN and not self.board.color_at(check_square):
                            return False
                else:
                    # Pour les noirs, vérifie les rangées inférieures
                    for rank in range(square // 8 - 1, -1, -1):
                        check_square = rank * 8 + check_file
                        if self.board.piece_at(check_square) == PAWN and self.board.color_at(check_square):
                            return False
        return True

    def _evaluate_pawn_structure(self):
        """Évalue la structure des pions."""
        score = 0
        
        # Compte les pions par colonne pour détecter les pions doublés/isolés
        white_pawn_files = {}
        black_pawn_files = {}
        
        for square in self.board.pieces(PAWN, WHITE):
            file = square % 8
            white_pawn_files[file] = white_pawn_files.get(file, 0) + 1
            
        for square in self.board.pieces(PAWN, not WHITE):
            file = square % 8
            black_pawn_files[file] = black_pawn_files.get(file, 0) + 1
        
        # Malus pour pions doublés
        for file, count in white_pawn_files.items():
            if count > 1:
                score -= 20 * (count - 1)
        for file, count in black_pawn_files.items():
            if count > 1:
                score += 20 * (count - 1)
        
        # Malus pour pions isolés (pas de pions alliés sur files adjacentes)
        for file in white_pawn_files:
            if (file-1 not in white_pawn_files) and (file+1 not in white_pawn_files):
                score -= 15
        for file in black_pawn_files:
            if (file-1 not in black_pawn_files) and (file+1 not in black_pawn_files):
                score += 15
                
        return score

    def _evaluate_center_control(self):
        """Évalue le contrôle des cases centrales."""
        center_squares = [27, 28, 35, 36]  # d4, e4, d5, e5
        extended_center = [18, 19, 20, 21, 26, 29, 34, 37, 42, 43, 44, 45]  # Centre étendu
        
        score = 0
        
        # Bonus pour pièces contrôlant le centre
        for square in center_squares:
            piece = self.board.piece_at(square)
            if piece:
                if self.board.color_at(square) == WHITE:
                    score += 30
                else:
                    score -= 30
                    
        for square in extended_center:
            piece = self.board.piece_at(square)
            if piece:
                if self.board.color_at(square) == WHITE:
                    score += 10
                else:
                    score -= 10
                    
        return score

    def _evaluate_king_safety(self):
        """Évalue la sécurité du roi."""
        score = 0
        
        # Position du roi
        white_king = self.board.king(WHITE)
        black_king = self.board.king(not WHITE)
        
        # En début/milieu de partie, le roi est plus sûr près du bord
        material = sum(PIECE_VALUES[piece_type] * len(self.board.pieces(piece_type, WHITE)) 
                      for piece_type in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN])
        
        if material > 2000:  # Milieu de partie
            # Roi blanc plus sûr en rangée 0-1
            if white_king // 8 <= 1:
                score += 20
            # Roi noir plus sûr en rangée 6-7
            if black_king // 8 >= 6:
                score -= 20
                
        return score

    def _order_moves(self, moves, maximizing):
        """Trie les mouvements pour optimiser l'élagage alpha-beta."""
        move_scores = []
        
        for move in moves:
            score = 0
            
            # 1) Captures en premier
            if self.board.is_capture(move):
                captured_piece = self.board.piece_at(move.to_square)
                if captured_piece:
                    score += PIECE_VALUES.get(captured_piece.piece_type, 0) * 10
            
            # 2) Checks
            self.board.push(move)
            if self.board.is_check():
                score += 50
            self.board.pop()
            
            # 3) Promotions
            if move.promotion:
                score += 900  # Valeur de la reine
                
            move_scores.append((score, move))
        
        # Tri par score décroissant
        move_scores.sort(key=lambda x: x[0], reverse=True)
        return [move for score, move in move_scores]

    def _should_extend_search(self):
        """Détermine si la recherche doit être étendue pour cette position."""
        # Extension uniquement pour les checks (plus sûr)
        if self.board.is_check():
            return True
        return False

    def minimax(self, depth, alpha, beta, maximizing):
        # Vérifier la mémoire transposition avec clé unique par IA
        board_key = (self.board.fen(), depth, maximizing, id(self))
        if board_key in self.transposition_table:
            cached_score, cached_move = self.transposition_table[board_key]
            return cached_score, cached_move
            
        # Extension de recherche pour les positions critiques
        if depth == 0 and self._should_extend_search():
            depth = 1
            
        if depth == 0 or self.board.is_game_over():
            return self.evaluate(), None

        best_move = None
        
        # Tri des mouvements pour optimiser l'élagage alpha-beta
        moves = self._order_moves(self.board.legal_moves, maximizing)
        if maximizing:
            max_eval = -10**9
            for move in moves:
                self.board.push(move)
                eval_score, _ = self.minimax(depth - 1, alpha, beta, False)
                self.board.pop()
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                if eval_score > alpha:
                    alpha = eval_score
                if beta <= alpha:
                    break
            # Stocker dans la mémoire transposition avec clé unique par IA
            self.transposition_table[board_key] = (max_eval, best_move)
            return max_eval, best_move
        else:
            min_eval = 10**9
            for move in moves:
                self.board.push(move)
                eval_score, _ = self.minimax(depth - 1, alpha, beta, True)
                self.board.pop()
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                if eval_score < beta:
                    beta = eval_score
                if beta <= alpha:
                    break
            # Stocker dans la mémoire transposition avec clé unique par IA
            self.transposition_table[board_key] = (min_eval, best_move)
            return min_eval, best_move

    def get_opening_move(self, board):
        """Retourne un coup d'ouverture si disponible dans le livre."""
        current_fen = board.fen()
        
        # Vérifier si la position actuelle est dans notre livre
        if current_fen in OPENING_BOOK:
            opening_moves = OPENING_BOOK[current_fen]
            
            # Choisir aléatoirement parmi les meilleures ouvertures
            # pour plus de variété et imprévisibilité
            chosen_move = random.choice(opening_moves)
            
            # Vérifier que le coup est légal
            try:
                move = board.push_san(chosen_move)
                board.pop()  # Annuler le coup pour ne pas modifier le board
                return board.san(move)
            except ValueError:
                # Si le coup n'est pas valide, passer au calcul normal
                return None
        
        return None

    def coup(self, board) -> str:
        # Utiliser la bibliothèque d'ouvertures pour les 10 premiers coups
        if self.opening_moves_played < 10:
            opening_move = self.get_opening_move(board)
            if opening_move:
                self.opening_moves_played += 1
                return opening_move
            else:
                # Si plus d'ouverture trouvée, passer au calcul normal
                self.opening_moves_played = 10  # Forcer la sortie du livre
        
        # Calcul normal avec l'IA
        self.board = board  # Utiliser le board actuel du jeu
        maximizing = self.board.turn == WHITE
        _, move = self.minimax(self.depth, -10**9, 10**9, maximizing)
        if move is None:
            raise ValueError("Aucun coup trouvé")
        return self.board.san(move)
