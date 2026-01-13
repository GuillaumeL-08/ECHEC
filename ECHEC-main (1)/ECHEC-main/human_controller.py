from chess import Move, QUEEN, WHITE, BLACK


class HumanController:
    """Gère l'interaction humain (drag-and-drop) pour jouer les coups."""

    def __init__(self, board, canvas, root, human_white: bool, human_black: bool, update_board_cb):
        self.board = board
        self.canvas = canvas
        self.root = root
        self.human_white = human_white
        self.human_black = human_black
        self.update_board_cb = update_board_cb  # callback pour mettre à jour l'échiquier
        self.selected_square = None

        # Bind du drag-and-drop sur le canvas
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def is_human_turn(self) -> bool:
        """True si c'est au tour d'un joueur humain de jouer."""
        if self.board.turn == WHITE:
            return self.human_white
        else:
            return self.human_black

    def maybe_schedule_ai_turn(self, jouer_cb):
        """Planifie le tour de l'IA si ce n'est pas à un humain de jouer."""
        if not self.is_human_turn():
            # On laisse un léger délai avant de jouer le coup IA
            self.root.after(500, jouer_cb)

    def on_press(self, event):
        """Début du drag : sélection de la pièce à déplacer."""
        # Si la partie est terminée ou ce n'est pas au tour de l'humain, on ignore
        if self.board.is_game_over() or not self.is_human_turn():
            return

        board_width = int(self.canvas.cget("width"))
        board_height = int(self.canvas.cget("height"))

        col = int(event.x / (board_width / 8))
        row = int(event.y / (board_height / 8))
        if col < 0 or col > 7 or row < 0 or row > 7:
            return

        rank = 7 - row
        file = col
        square = rank * 8 + file

        piece = self.board.piece_at(square)
        if piece is None:
            return
        # Vérifie que la pièce appartient bien au camp au trait
        if (self.board.turn == WHITE and not piece.color) or (self.board.turn == BLACK and piece.color):
            return
        self.selected_square = square

    def on_release(self, event):
        """Fin du drag : tentative de jouer le coup sur la case de relâchement."""
        if self.board.is_game_over() or not self.is_human_turn():
            return

        if self.selected_square is None:
            return

        board_width = int(self.canvas.cget("width"))
        board_height = int(self.canvas.cget("height"))

        col = int(event.x / (board_width / 8))
        row = int(event.y / (board_height / 8))
        if col < 0 or col > 7 or row < 0 or row > 7:
            self.selected_square = None
            return

        rank = 7 - row
        file = col
        square = rank * 8 + file

        from_square = self.selected_square
        to_square = square

        move = Move(from_square, to_square)
        if move not in self.board.legal_moves:
            # Essaye une promotion en reine si nécessaire
            move = Move(from_square, to_square, promotion=QUEEN)
            if move not in self.board.legal_moves:
                # Coup illégal, on annule la sélection
                self.selected_square = None
                return

        # Joue le coup humain
        self.board.push(move)
        self.selected_square = None
        # Met à jour l'affichage
        self.update_board_cb()
        # Et laisse éventuellement l'IA jouer derrière
        self.maybe_schedule_ai_turn(self._jouer_after_human)

    def _jouer_after_human(self):
        """Callback interne pour déclencher le tour IA après un coup humain.
        La méthode réelle 'jouer' est fournie via update_board_cb -> Chess_UI.gestion.
        Ce wrapper sera remplacé par Chess_UI lors de l'initialisation si nécessaire.
        """
        # Cette méthode sera reliée à Chess_UI.jouer depuis canvas_tkinter.
        pass
