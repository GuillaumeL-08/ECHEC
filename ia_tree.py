from chess import PAWN, KNIGHT, BISHOP, ROOK, QUEEN
from chess import WHITE


PIECE_VALUES = {
    PAWN: 150,   # on augmente un peu la valeur des pions
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
}


class TreeIA:
    def __init__(self, board, depth=2):
        self.board = board
        self.depth = depth

    def evaluate(self) -> int:
        """Évalue la position du point de vue des BLANCS (score > 0 = bon pour les blancs)."""
        # Gestion explicite des fins de partie
        if self.board.is_checkmate():
            # Le camp au trait est maté : si c'est les blancs qui sont au trait, c'est très mauvais pour eux
            return -100000 if self.board.turn == WHITE else 100000
        if self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.can_claim_threefold_repetition():
            return 0

        # 1) Matériel
        score = 0
        for piece_type in PIECE_VALUES:
            score += PIECE_VALUES[piece_type] * len(self.board.pieces(piece_type, WHITE))
            score -= PIECE_VALUES[piece_type] * len(self.board.pieces(piece_type, not WHITE))

        # 1.bis) Bonus de position pour les pions (avance + centre)
        # On parcourt les pions blancs
        for square in self.board.pieces(PAWN, WHITE):
            rank = square // 8  # 0 (rangée 1) -> 7 (rangée 8)
            file = square % 8   # 0 (colonne a) -> 7 (colonne h)
            # plus le pion est avancé, plus il est valorisé
            score += rank * 10
            # bonus pour le centre (colonnes c, d, e, f)
            if 2 <= file <= 5:
                score += 15

        # Pions noirs
        for square in self.board.pieces(PAWN, not WHITE):
            rank = square // 8
            file = square % 8
            # pour les noirs, plus le pion est "bas" (vers rangée 0) moins c'est bon pour les blancs
            score -= (7 - rank) * 10
            if 2 <= file <= 5:
                score -= 15

        # 2) Mobilité : on compte plus de mobilité pour les blancs et on enlève celle des noirs
        # (approximation : on génère les coups au trait et on pondère en fonction du trait)
        mobility = len(list(self.board.legal_moves))
        if self.board.turn == WHITE:
            score += 10 * mobility
        else:
            score -= 10 * mobility

        # 3) Bonus pour les positions d'attaque (échecs donnés par le camp au trait)
        if self.board.is_check():
            if self.board.turn == WHITE:
                # les blancs viennent de donner échec
                score += 50
            else:
                # les noirs viennent de donner échec
                score -= 50

        # On renvoie toujours un score du point de vue des BLANCS
        return score

    def minimax(self, depth, alpha, beta, maximizing):
        if depth == 0 or self.board.is_game_over():
            return self.evaluate(), None

        best_move = None
        if maximizing:
            max_eval = -10**9
            for move in self.board.legal_moves:
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
            return max_eval, best_move
        else:
            min_eval = 10**9
            for move in self.board.legal_moves:
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
            return min_eval, best_move

    def coup(self) -> str:
        # On décide si ce noeud est un max ou un min en fonction de qui joue :
        # les blancs essaient de maximiser le score, les noirs de le minimiser.
        maximizing = self.board.turn == WHITE
        _, move = self.minimax(self.depth, -10**9, 10**9, maximizing)
        if move is None:
            raise ValueError("Aucun coup trouvé")
        return self.board.san(move)
