from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
from chess import *
from human_controller import HumanController
import os

board_width = 1024
board_height = 1024


class Chess_UI:
    def __init__(self, root:Tk, board:Board, J_Blanc, J_Noir):
        base_dir = os.path.join(os.path.dirname(__file__), 'img')
        self.img_dict = {
            'p': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'pion_noir.png')).resize((100, 100))),
            'b': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'fou_noir.png')).resize((100, 100))),
            'q': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'reine_noire.png')).resize((100, 100))),
            'k': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'roi_noir.png')).resize((100, 100))),
            'n': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'cavalier_noir.png')).resize((100, 100))),
            'r': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'tour_noire.png')).resize((100, 100))),
            'P': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'pion_blanc.png')).resize((100, 100))),
            'B': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'fou_blanc.png')).resize((100, 100))),
            'Q': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'reine_blanche.png')).resize((100, 100))),
            'K': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'roi_blanc.png')).resize((100, 100))),
            'N': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'cavalier_blanc.png')).resize((100, 100))),
            'R': ImageTk.PhotoImage(Image.open(os.path.join(base_dir, 'tour_blanche.png')).resize((100, 100))),
        }
        self.root = root
        self.board = board
        self.Joueur_Blanc = J_Blanc
        self.Joueur_Noir = J_Noir
        self.human_white = (J_Blanc is None)
        self.human_black = (J_Noir is None)
        self.mainframe = ttk.Frame(self.root)
        self.mainframe.grid()


        for i in range(8):
            label = Label(self.mainframe, text=chr(ord('A') + i), bg='white')
            label.grid(row=0, column=i + 1, sticky=(S))
            label = Label(self.mainframe, text=chr(ord('1') + i), bg='white')
            label.grid(row=i + 1, column=0, sticky=(E))

        self.history_white = []
        self.history_black = []
        self.history_white_var = StringVar(value=self.history_white)
        self.history_white_listbox = Listbox(self.mainframe, listvariable=self.history_white_var, bg="white", height=48)
        self.history_white_listbox.grid(row=1, column=9, rowspan=8, sticky=(N))

        self.history_black_var = StringVar(value=self.history_black)
        self.history_black_listbox = Listbox(self.mainframe, listvariable=self.history_black_var, bg="white", height=48)
        self.history_black_listbox.grid(row=1, column=10, rowspan=8, sticky=(N))

        self.canvas = Canvas(self.mainframe, bg="black", width=board_width, height=board_height)
        self.canvas.grid(row=1, column=1, columnspan=8, rowspan=8)
        self.bg_img = Image.open(os.path.join(base_dir, 'plateau.png'))
        self.bg_photo = ImageTk.PhotoImage(self.bg_img)
        self.canvas.create_image(board_width / 2, board_height / 2, image=self.bg_photo)

        self.pieces_list = []

        self.human_controller = HumanController(
            board=self.board,
            canvas=self.canvas,
            root=self.root,
            human_white=self.human_white,
            human_black=self.human_black,
            update_board_cb=self.update_board,
        )

        self.human_controller._jouer_after_human = self.jouer

        self.update_board()

    def get_x_from_col(self, col:int) -> float:
        if col < 0 or col > 7:
            raise ValueError(col)
        return board_width / 8 * col + board_width / 16

    def get_y_from_row(self, row:int) -> float:
        if row < 0 or row > 7:
            raise ValueError(row)
        return board_height / 8 * row + board_height / 16

    def display_piece(self, piece:Piece, col:int, row:int) -> None:
        self.pieces_list.append(self.canvas.create_image(self.get_x_from_col(col), self.get_y_from_row(row), image=self.img_dict[piece]))

    def update_board(self):
        for piece in self.pieces_list:
            self.canvas.delete(piece)
        row = 0
        col = 0
        for piece in self.board.board_fen():
            if '1' <= piece <= '8':
                col += ord(piece) - ord('0')
            elif piece == '/':
                col = 0
                row += 1
            else:
                self.display_piece(piece, col, row)
                col += 1

        if self.board.turn == WHITE:
            self.history_white_listbox.update()
        else:
            self.history_black_listbox.update()


        self.human_controller.maybe_schedule_ai_turn(self.jouer)

    def update_history_white(self, entry):
        self.history_white.append(entry)
        self.history_white_var.set(self.history_white)

    def update_history_black(self, entry):
        self.history_black.append(entry)
        self.history_black_var.set(self.history_black)

    def jouer(self):
        if self.board.is_game_over():
            res = self.board.result()
            if res == "1-0":
                res = "Les blancs ont gagné !"
            elif res == "0-1":
                res = "Les noir ont gagné !"
            else:
                res = "Egalité !"

            if hasattr(self.Joueur_Blanc, 'end_game'):
                self.Joueur_Blanc.end_game(self.board.result(), self.board, color=WHITE)
            if hasattr(self.Joueur_Noir, 'end_game'):
                self.Joueur_Noir.end_game(self.board.result(), self.board, color=BLACK)

            stats_text = ""
            if hasattr(self.Joueur_Blanc, 'get_learning_stats'):
                stats = self.Joueur_Blanc.get_learning_stats()
                if stats:
                    stats_text += f"IA Blanche: {stats['games_played']} parties, {stats['positions_learned']} positions apprises\n"
            if hasattr(self.Joueur_Noir, 'get_learning_stats'):
                stats = self.Joueur_Noir.get_learning_stats()
                if stats:
                    stats_text += f"IA Noire: {stats['games_played']} parties, {stats['positions_learned']} positions apprises\n"

            self.canvas.create_text(
                240, 220, text=f"Partie terminée : {res}",
                font=("Arial", 24, "bold"), fill="red"
            )
            if stats_text:
                self.canvas.create_text(
                    240, 260, text=stats_text,
                    font=("Arial", 12), fill="blue"
                )
            return 0

        if self.board.turn == WHITE:
            if self.human_white:
                return
            self.board.push_san(self.Joueur_Blanc.coup(self.board))
        else:
            if self.human_black:
                return
            self.board.push_san(self.Joueur_Noir.coup(self.board))

        self.update_board()