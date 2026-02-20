from random import choice


class RandomIA:
    def __init__(self, board=None):
        self.board = board

    def coup(self, board) -> str:
        moves = list(board.legal_moves)
        if not moves:
            raise ValueError("Aucun coup légal disponible")
        move = choice(moves)
        return board.san(move)