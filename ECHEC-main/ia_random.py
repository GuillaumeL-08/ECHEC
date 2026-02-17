from random import choice


class RandomIA:
    """IA très simple qui joue un coup légal aléatoire sur le plateau fourni."""

    def __init__(self, board=None):
        # BUG FIX: board est optionnel car coup() reçoit le board en paramètre
        self.board = board

    def coup(self, board) -> str:
        """Retourne un coup légal aléatoire au format SAN pour python-chess."""
        # BUG FIX: accepte le board en paramètre (cohérent avec l'appel dans canvas_tkinter.py)
        moves = list(board.legal_moves)
        if not moves:
            raise ValueError("Aucun coup légal disponible")
        move = choice(moves)
        return board.san(move)