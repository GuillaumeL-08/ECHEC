from chess import Move, QUEEN, WHITE, BLACK


class HumanController:
    def __init__(self, board, canvas, root, human_white: bool, human_black: bool, update_board_cb):
        self.board = board
        self.canvas = canvas
        self.root = root
        self.human_white = human_white
        self.human_black = human_black
        self.update_board_cb = update_board_cb
        self.selected_square = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def is_human_turn(self) -> bool:
        if self.board.turn == WHITE:
            return self.human_white
        else:
            return self.human_black

    def maybe_schedule_ai_turn(self, jouer_cb):
        if not self.is_human_turn():
            self.root.after(500, jouer_cb)

    def on_press(self, event):
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
        if (self.board.turn == WHITE and not piece.color) or (self.board.turn == BLACK and piece.color):
            return
        self.selected_square = square

    def on_release(self, event):
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
            move = Move(from_square, to_square, promotion=QUEEN)
            if move not in self.board.legal_moves:
                self.selected_square = None
                return

        self.board.push(move)
        self.selected_square = None
        self.update_board_cb()
        self.maybe_schedule_ai_turn(self._jouer_after_human)

    def _jouer_after_human(self):
        pass