from chess import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, WHITE, BLACK, Board
from typing import Optional
from collections import Counter
import random

from pst_tables import (
    PIECE_VALUES, PST, PST_BLACK,
    PAWN_ENDGAME, PAWN_ENDGAME_BLACK,
    ROOK_ENDGAME, ROOK_ENDGAME_BLACK,
    QUEEN_ENDGAME, QUEEN_ENDGAME_BLACK,
    KING_ENDGAME, KING_ENDGAME_BLACK,
)


class Evaluator:
    """
    Classe d'évaluation de position pour l'IA. Fournit une évaluation numérique 
    de la position actuelle du plateau, positive 
    si avantage pour les blancs, négative si avantage pour les noirs.
    """
    def __init__(self, get_board, get_eval_noise=None, get_eval_depth=None, learning_manager=None):
        self._get_board = get_board
        self._get_eval_noise = get_eval_noise or (lambda: 0)
        self._get_eval_depth = get_eval_depth or (lambda: 0)
        self.learning_manager = learning_manager

    @property
    def board(self) -> Optional[Board]:
        return self._get_board()

    def _material_score(self) -> int:
        """Calcule une évaluation de base basée sur le matériel (valeur des pièces)."""
        score = 0
        for pt in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN):
            score += PIECE_VALUES[pt] * (
                len(self.board.pieces(pt, WHITE)) - len(self.board.pieces(pt, BLACK))
            )
        return score

    def _is_endgame(self) -> bool:
        """Détermine si la position est une finale, ce qui affecte l'évaluation des pièces."""
        queens = len(self.board.pieces(QUEEN, WHITE)) + len(self.board.pieces(QUEEN, BLACK))
        minors_w = len(self.board.pieces(KNIGHT, WHITE)) + len(self.board.pieces(BISHOP, WHITE))
        minors_b = len(self.board.pieces(KNIGHT, BLACK)) + len(self.board.pieces(BISHOP, BLACK))
        return queens == 0 or (queens == 2 and minors_w <= 1 and minors_b <= 1)

    def _king_distance(self, sq1: int, sq2: int) -> int:
        """Calcule la distance de Chebyshev entre deux cases, utilisée pour évaluer les positions de roi en finale."""
        r1, f1 = sq1 // 8, sq1 % 8
        r2, f2 = sq2 // 8, sq2 % 8
        return max(abs(r1 - r2), abs(f1 - f2))

    def _corner_distance(self, sq: int) -> int:
        """Calcule la distance de Chebyshev d'une case à la plus proche des quatre cases de coin, utilisée pour évaluer les positions de roi en finale."""
        r, f = sq // 8, sq % 8
        return min(r, 7 - r) + min(f, 7 - f)

    def _is_winning_endgame(self, mat: int) -> int:
        """
        Détermine si la position est une finale gagnante pour l'un des camps, en se basant sur une évaluation matérielle grossière.
        Retourne 1 si avantage blanc, -1 si avantage noir, 0 sinon.
        """
        if mat >= 500:
            return 1
        if mat <= -500:
            return -1
        return 0

    def _castling_score(self, wk, bk) -> int:
        """Évalue la position des rois par rapport au droit de roque et à la sécurité du roi."""
        score = 0
        b = self.board

        w_can_castle = b.has_castling_rights(WHITE)
        b_can_castle = b.has_castling_rights(BLACK)

        if wk is not None:
            w_castled_kingside  = (wk == 6  and not b.has_kingside_castling_rights(WHITE))
            w_castled_queenside = (wk == 2  and not b.has_queenside_castling_rights(WHITE))
            if w_castled_kingside or w_castled_queenside:
                score += 60
            elif not w_can_castle and wk not in (6, 2):
                score -= 50
            elif w_can_castle and wk == 4:
                score -= 10

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
        """Évalue le contrôle du centre, en accordant plus de poids au contrôle des cases centrales strictes (d4, d5, e4, e5) en début de partie."""
        b = self.board
        ply = b.ply()

        if ply > 60:
            return 0

        weight = max(0.0, 1.0 - ply / 60.0)

        CENTER_STRICT   = [27, 28, 35, 36]
        CENTER_EXTENDED = [18, 19, 20, 21, 26, 29, 34, 37, 42, 43, 44, 45]

        score = 0

        for sq in CENTER_STRICT:
            piece = b.piece_at(sq)
            if piece:
                val = 30 if piece.piece_type == PAWN else 15
                score += val if piece.color == WHITE else -val
            w_attacks = b.is_attacked_by(WHITE, sq)
            b_attacks = b.is_attacked_by(BLACK, sq)
            if w_attacks and not b_attacks: score += 10
            elif b_attacks and not w_attacks: score -= 10

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
        """Évalue le développement des pièces mineures en début de partie, en pénalisant les pièces qui n'ont pas encore bougé de leur position initiale."""
        b = self.board
        ply = b.ply()

        if ply > 40:
            return 0

        weight = max(0.0, 1.0 - ply / 40.0)
        score = 0

        W_MINOR_START = {1: KNIGHT, 6: KNIGHT, 2: BISHOP, 5: BISHOP}
        B_MINOR_START = {57: KNIGHT, 62: KNIGHT, 58: BISHOP, 61: BISHOP}

        w_undeveloped = 0
        b_undeveloped = 0
        for sq, pt in W_MINOR_START.items():
            piece = b.piece_at(sq)
            if piece and piece.color == WHITE and piece.piece_type == pt:
                score -= 12
                w_undeveloped += 1
        for sq, pt in B_MINOR_START.items():
            piece = b.piece_at(sq)
            if piece and piece.color == BLACK and piece.piece_type == pt:
                score += 12
                b_undeveloped += 1

        if ply >= 4:
            moves = list(b.move_stack)
            white_moves = [m for i, m in enumerate(moves) if i % 2 == 0]
            black_moves = [m for i, m in enumerate(moves) if i % 2 == 1]

            def double_move_penalty(camp_moves, undeveloped, sign):
                """Pénalité pour les pièces mineures qui ont bougé mais sont retournées à leur position initiale, ce qui indique un développement inefficace."""
                pen = 0
                for j in range(1, len(camp_moves)):
                    prev, curr = camp_moves[j-1], camp_moves[j]
                    if curr.from_square == prev.to_square and undeveloped >= 1:
                        pen += sign * 18
                return pen

            score += double_move_penalty(white_moves, w_undeveloped, -1)
            score += double_move_penalty(black_moves, b_undeveloped, +1)

        if ply < 12:
            wq_sq = list(b.pieces(QUEEN, WHITE))
            bq_sq = list(b.pieces(QUEEN, BLACK))
            if wq_sq and wq_sq[0] != 3 and w_undeveloped >= 2:
                score -= 12 * w_undeveloped
            if bq_sq and bq_sq[0] != 59 and b_undeveloped >= 2:
                score += 12 * b_undeveloped

        for sq in b.pieces(KNIGHT, WHITE):
            if sq // 8 > 0:
                score += 8
        for sq in b.pieces(BISHOP, WHITE):
            if sq // 8 > 0:
                score += 6
        for sq in b.pieces(KNIGHT, BLACK):
            if sq // 8 < 7:
                score -= 8
        for sq in b.pieces(BISHOP, BLACK):
            if sq // 8 < 7:
                score -= 6

        return int(score * weight)

    def evaluate(self) -> int:
        """Calcule une évaluation de la position actuelle du plateau, positive si avantage pour les blancs, négative si avantage pour les noirs."""
        b = self.board
        if b.is_checkmate():
            depth_bonus = self._get_eval_depth()
            return -99000 - depth_bonus
        if b.is_stalemate() or b.is_insufficient_material() or b.is_seventyfive_moves():
            return 0

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
            score += self._king_shield_score()

        score += self._open_files_score()

        if endgame and not b.is_check():
            legal_moves = list(b.legal_moves)
            if len(legal_moves) <= 2:
                opp_has_moves = any(
                    b.piece_at(m.from_square) and b.piece_at(m.from_square).piece_type != KING
                    for m in legal_moves
                )
                if not opp_has_moves and len(legal_moves) > 0:
                    pat_penalty = -300 if b.turn == WHITE else 300
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

        noise = self._get_eval_noise()
        if noise > 0:
            score += random.randint(-noise, noise)

        return score if b.turn == WHITE else -score

    def _pawn_structure_fast(self) -> int:
        """Évalue la structure des pions. Pénalise les pions doublés, isolés et arriérés, et récompense les pions passés."""
        score = 0
        wp = self.board.pieces(PAWN, WHITE)
        bp = self.board.pieces(PAWN, BLACK)

        w_files = set(sq % 8 for sq in wp)
        b_files = set(sq % 8 for sq in bp)

        wf_count = Counter(sq % 8 for sq in wp)
        bf_count = Counter(sq % 8 for sq in bp)
        for f, c in wf_count.items():
            if c > 1: score -= 20 * (c - 1)
        for f, c in bf_count.items():
            if c > 1: score += 20 * (c - 1)

        for f in w_files:
            if (f-1) not in w_files and (f+1) not in w_files:
                score -= 15
        for f in b_files:
            if (f-1) not in b_files and (f+1) not in b_files:
                score += 15

        for sq in wp:
            rank = sq // 8
            f = sq % 8
            if not any(s // 8 > rank and s % 8 == f for s in bp):
                score += 20 + rank * 8
            support_files = {f - 1, f + 1} & w_files
            can_be_supported = any(
                s % 8 in support_files and s // 8 <= rank for s in wp
            )
            if not can_be_supported:
                front_sq = sq + 8
                if front_sq < 64:
                    controlled_by_black = any(
                        s % 8 in {f - 1, f + 1} and s // 8 == rank + 1 for s in bp
                    )
                    if controlled_by_black:
                        score -= 25

        for sq in bp:
            rank = sq // 8
            f = sq % 8
            if not any(s // 8 < rank and s % 8 == f for s in wp):
                score -= 20 + (7 - rank) * 8
            support_files = {f - 1, f + 1} & b_files
            can_be_supported = any(
                s % 8 in support_files and s // 8 >= rank for s in bp
            )
            if not can_be_supported:
                front_sq = sq - 8
                if front_sq >= 0:
                    controlled_by_white = any(
                        s % 8 in {f - 1, f + 1} and s // 8 == rank - 1 for s in wp
                    )
                    if controlled_by_white:
                        score += 25

        return score

    def _open_files_score(self) -> int:
        """Évalue les tours sur les colonnes ouvertes, en accordant plus de poids aux tours sur les colonnes ouvertes sans pions adverses en fin de partie."""
        b = self.board
        wp = b.pieces(PAWN, WHITE)
        bp = b.pieces(PAWN, BLACK)
        w_files = set(sq % 8 for sq in wp)
        b_files = set(sq % 8 for sq in bp)
        score = 0

        for sq in b.pieces(ROOK, WHITE):
            f = sq % 8
            if f not in w_files and f not in b_files:
                score += 25   
            elif f not in w_files:
                score += 12  

        for sq in b.pieces(ROOK, BLACK):
            f = sq % 8
            if f not in w_files and f not in b_files:
                score -= 25
            elif f not in b_files:
                score -= 12

        return score

    def _king_shield_score(self) -> int:
        """Évalue la sécurité du roi en fonction de la présence de pions de bouclier devant lui, en accordant plus de poids à ces facteurs en début de partie."""
        b = self.board
        if self._is_endgame():
            return 0
        score = 0

        wk = b.king(WHITE)
        bk = b.king(BLACK)

        def shield(king_sq, color, sign):
            """
            Calcule une évaluation de la sécurité du roi basée sur la présence de pions de bouclier devant lui, 
            en accordant plus de poids à ces facteurs en début de partie.
            """
            if king_sq is None:
                return 0
            kf = king_sq % 8
            kr = king_sq // 8
            val = 0
            front_rank = kr + 1 if color == WHITE else kr - 1
            if 0 <= front_rank <= 7:
                for df in (-1, 0, 1):
                    f = kf + df
                    if 0 <= f <= 7:
                        sq = front_rank * 8 + f
                        piece = b.piece_at(sq)
                        if piece and piece.piece_type == PAWN and piece.color == color:
                            val += 20  
                front_rank2 = kr + 2 if color == WHITE else kr - 2
                if 0 <= front_rank2 <= 7:
                    for df in (-1, 0, 1):
                        f = kf + df
                        if 0 <= f <= 7:
                            sq = front_rank2 * 8 + f
                            piece = b.piece_at(sq)
                            if piece and piece.piece_type == PAWN and piece.color == color:
                                val += 10 
            return val * sign

        score += shield(wk, WHITE, +1)
        score += shield(bk, BLACK, -1)
        return score

    def _mobility_score(self) -> int:
        """Évalue la mobilité de chaque camp, en accordant plus de poids à ce facteur en milieu de partie."""
        b = self.board
        w_mob = sum(1 for _ in b.generate_pseudo_legal_moves(b.occupied_co[WHITE]))
        b_mob = sum(1 for _ in b.generate_pseudo_legal_moves(b.occupied_co[BLACK]))
        return (w_mob - b_mob)
