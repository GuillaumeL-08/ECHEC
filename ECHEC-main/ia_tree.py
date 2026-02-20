from chess import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, Board, WHITE, BLACK, Move
from typing import Optional
import random
import time
from collections import OrderedDict
from learning_manager import LearningManager
from pst_tables import PIECE_VALUES, zobrist_hash
from evaluator import Evaluator


class BoundedTT:
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
                self._data.popitem(last=False)
        self._data[key] = (score, flag, depth, move)

    def clear(self):
        self._data.clear()


class TreeIA:
    MAX_DEPTH = 10
    TIME_LIMIT = 2.0
    TT_SIZE = 400_000

    def __init__(self, depth=4, enable_learning=True, time_limit=2.0):
        self.depth = depth
        self.time_limit = time_limit
        self.board: Optional[Board] = None
        self.tt = BoundedTT(self.TT_SIZE)
        self.killer_moves = [[None, None] for _ in range(self.MAX_DEPTH + 2)]
        self.history = {}
        self.enable_learning = enable_learning
        self._start_time = 0.0
        self._nodes = 0
        self._eval_noise = 0
        self._eval_depth = 0
        self._piece_move_count = {}

        if enable_learning:
            self.learning_manager = LearningManager()
            self.learning_manager.start_new_game()
        else:
            self.learning_manager = None

        self._evaluator = Evaluator(
            get_board=lambda: self.board,
            get_eval_noise=lambda: self._eval_noise,
            get_eval_depth=lambda: self._eval_depth,
            learning_manager=self.learning_manager,
        )

    def evaluate(self) -> int:
        return self._evaluator.evaluate()

    def _is_endgame(self) -> bool:
        return self._evaluator._is_endgame()

    def _material_score(self) -> int:
        return self._evaluator._material_score()

    def _move_score(self, move: Move, depth: int) -> int:
        score = 0
        b = self.board

        if self._is_repetition_move(move):
            score -= 500

        if b.is_capture(move):
            victim = b.piece_at(move.to_square)
            aggressor = b.piece_at(move.from_square)
            if victim and aggressor:
                score += 10 * PIECE_VALUES.get(victim.piece_type, 0) \
                            - PIECE_VALUES.get(aggressor.piece_type, 0)
            else:
                score += 500

        if move.promotion:
            score += PIECE_VALUES.get(move.promotion, 0)

        ply = self.depth - depth
        if 0 <= ply < len(self.killer_moves):
            if move == self.killer_moves[ply][0]:
                score += 90
            elif move == self.killer_moves[ply][1]:
                score += 80

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
        if len(self.history) > 8192:
            self.history = {k: v // 2 for k, v in self.history.items()}

    def quiescence(self, alpha: int, beta: int, depth: int = 0) -> int:
        self._nodes += 1
        self._eval_depth = depth
        stand_pat = self.evaluate()

        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        captures = [m for m in self.board.legal_moves if self.board.is_capture(m)]
        captures = self._order_moves(captures, 0)

        for move in captures:
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

    def minimax(self, depth: int, alpha: int, beta: int, maximizing: bool) -> tuple:
        self._nodes += 1

        if self._nodes % 2048 == 0 and time.time() - self._start_time > self.time_limit:
            return None, None

        b = self.board

        if b.is_repetition(2):
            mat = self._material_score()
            if (maximizing and mat > 100) or (not maximizing and mat < -100):
                return -200, None
            return 0, None

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

        if depth == 0 or b.is_game_over():
            self._eval_depth = depth
            score = self.quiescence(alpha, beta, depth)
            return score, None

        R = 2
        if (depth >= R + 1
                and not b.is_check()
                and not self._is_endgame()
                and abs(alpha) < 90000):
            b.push(Move.null())
            null_score, _ = self.minimax(depth - R - 1, -beta, -beta + 1, not maximizing)
            b.pop()
            if null_score is not None and -null_score >= beta:
                return beta, None

        legal = list(b.legal_moves)
        if not legal:
            return self.evaluate(), None

        if tt_move and tt_move in legal:
            legal.remove(tt_move)
            legal.insert(0, tt_move)
        moves = self._order_moves(legal, depth)

        best_move = None
        original_alpha = alpha
        best_score = -10**9

        for i, move in enumerate(moves):
            is_capture = b.is_capture(move)
            b.push(move)
            if i >= 4 and depth >= 3 and not b.is_check() and not is_capture:
                score, _ = self.minimax(depth - 2, -beta, -alpha, not maximizing)
                if score is not None and -score > alpha:
                    score, _ = self.minimax(depth - 1, -beta, -alpha, not maximizing)
            else:
                score, _ = self.minimax(depth - 1, -beta, -alpha, not maximizing)
            b.pop()

            if score is None:
                return None, None

            score = -score

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
            if alpha >= beta:
                if not is_capture:
                    self._update_killer(move, depth)
                    self._update_history(move, depth)
                break

        flag = (BoundedTT.EXACT if original_alpha < best_score < beta
                else BoundedTT.LOWER if best_score >= beta
                else BoundedTT.UPPER)
        self.tt.put(zkey, best_score, flag, depth, best_move)
        return best_score, best_move

    def _is_repetition_move(self, move: Move) -> bool:
        if self.board is None:
            return False
        self.board.push(move)
        is_rep = self.board.is_repetition(2)
        self.board.pop()
        return is_rep

    def iterative_deepening(self) -> Move:
        self._start_time = time.time()
        self._nodes = 0
        maximizing = self.board.turn == WHITE

        legal = list(self.board.legal_moves)
        if not legal:
            raise ValueError("Aucun coup légal disponible")

        non_repeating = [m for m in legal if not self._is_repetition_move(m)]
        best_move = non_repeating[0] if non_repeating else legal[0]

        prev_score = 0
        ASPIRATION_DELTA = 50

        for current_depth in range(1, self.MAX_DEPTH + 1):
            if current_depth <= 2:
                alpha, beta = -10**9, 10**9
            else:
                alpha = prev_score - ASPIRATION_DELTA
                beta  = prev_score + ASPIRATION_DELTA

            while True:
                score, move = self.minimax(current_depth, alpha, beta, maximizing)

                if score is None:
                    break

                if score <= alpha:
                    alpha -= ASPIRATION_DELTA * 2
                elif score >= beta:
                    beta += ASPIRATION_DELTA * 2
                else:
                    break

            if score is None or move is None:
                break

            best_move = move
            prev_score = score
            elapsed = time.time() - self._start_time
            if elapsed > self.time_limit * 0.85:
                break

        return best_move

    def coup(self, board: Board) -> str:
        self.board = board
        self.killer_moves = [[None, None] for _ in range(self.MAX_DEPTH + 2)]

        if self.learning_manager:
            eps = self.learning_manager.exploration_rate

            if self.learning_manager.should_explore():
                legal = list(board.legal_moves)
                if legal:
                    non_rep = [m for m in legal if not self._is_repetition_move(m)]
                    move = random.choice(non_rep if non_rep else legal)
                    self._track_piece_move(board, move)
                    self.learning_manager.record_move(board, move, self.evaluate())
                    return board.san(move)

            self._eval_noise = int(eps * 320)
        else:
            self._eval_noise = 0

        move = self.iterative_deepening()
        self._eval_noise = 0
        self._track_piece_move(board, move)

        if self.learning_manager:
            self.learning_manager.record_move(board, move, self.evaluate())

        return board.san(move)

    def _track_piece_move(self, board: Board, move: Move):
        if board.ply() > 40:
            return
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type in (KNIGHT, BISHOP):
            dest = move.to_square
            self._piece_move_count[dest] = self._piece_move_count.get(dest, 0) + 1
            if move.from_square in self._piece_move_count:
                old_count = self._piece_move_count.pop(move.from_square)
                self._piece_move_count[dest] = max(
                    self._piece_move_count[dest], old_count + 1
                )

    def end_game(self, result: str, board=None, color=None):
        if self.learning_manager:
            final_board = board or getattr(self, 'board', None) or Board()
            if color is None:
                if final_board is not None and hasattr(final_board, 'turn'):
                    color = not final_board.turn
                else:
                    color = WHITE
            self.learning_manager.end_game(result, final_board, color=color)
            self.learning_manager.start_new_game()
        self.tt.clear()
        self.history = {}
        self._piece_move_count = {}

    def _reset_for_new_game(self):
        self.tt.clear()
        self.history = {}
        self._piece_move_count = {}
        self.killer_moves = [[None, None] for _ in range(self.MAX_DEPTH + 2)]

    def get_learning_stats(self):
        if self.learning_manager:
            return self.learning_manager.get_learning_stats()
        return None