from random import choice


class RandomIA:
    """IA très simple qui joue un coup légal aléatoire sur le plateau fourni."""

    def __init__(self, board):
        self.board = board

    def coup(self) -> str:
        """Retourne un coup légal aléatoire au format SAN pour python-chess."""
        moves = list(self.board.legal_moves)
        if not moves:
            # Normalement on ne devrait pas arriver ici car le plateau vérifie la fin de partie
            raise ValueError("Aucun coup légal disponible")
        move = choice(moves)
        return self.board.san(move)
