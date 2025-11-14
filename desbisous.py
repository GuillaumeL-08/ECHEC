from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
from chess import *
from random import choice


# ----------------------------------------------------------------------
# Joueur humain qui entre les coups dans la console
# ----------------------------------------------------------------------
class JoueurHumain:
    def __init__(self, board):
        self.board = board

    def coup(self):
        while True:
            try:
                print("\nPosition actuelle :")
                print(self.board)

                mv = input("Entrez votre coup (format SAN, ex: e4, Nf3, O-O...) : ")

                # Vérifie la validité
                self.board.parse_san(mv)

                return mv
            except:
                print("❌ Coup invalide, réessayez.")


# ----------------------------------------------------------------------
# Joueur qui joue un coup aléatoire parmi les coups légaux
# ----------------------------------------------------------------------
class JoueurAleatoire:
    def __init__(self, board):
        self.board = board

    def coup(self):
        coups_legaux = list(self.board.legal_moves)
        coup_choisi = choice(coups_legaux)
        return self.board.san(coup_choisi)


# ----------------------------------------------------------------------
# INTERFACE GRAPHIQUE
# ----------------------------------------------------------------------
class Chess_UI:

    def __init__(self, root: Tk, board: Board, J_Blanc, J_Noir):

        self.root = root

        # mettre en plein écran
        self.root.state("zoomed")  

        # IMPORTANT : force Tkinter à calculer la taille réelle de la fenêtre
        self.root.update_idletasks()

        # maintenant on peut récupérer la taille correcte
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # plateau = 90% du plus petit côté
        plateau_size = int(min(screen_w, screen_h) * 0.90)

        global board_width, board_height
        board_width = plateau_size
        board_height = plateau_size

        square_size = board_width // 8

        # -------------------------------------------------------------
        # CHARGEMENT DES IMAGES REDIMENSIONNÉES
        # -------------------------------------------------------------
        def load(path):
            return ImageTk.PhotoImage(Image.open(path).resize((square_size, square_size)))

        self.img_dict = {
            'p': load('img/pion_noir.png'),
            'b': load('img/fou_noir.png'),
            'q': load('img/reine_noire.png'),
            'k': load('img/roi_noir.png'),
            'n': load('img/cavalier_noir.png'),
            'r': load('img/tour_noire.png'),
            'P': load('img/pion_blanc.png'),
            'B': load('img/fou_blanc.png'),
            'Q': load('img/reine_blanche.png'),
            'K': load('img/roi_blanc.png'),
            'N': load('img/cavalier_blanc.png'),
            'R': load('img/tour_blanche.png'),
        }

        self.board = board
        self.Joueur_Blanc = J_Blanc
        self.Joueur_Noir = J_Noir

        self.mainframe = ttk.Frame(self.root)
        self.mainframe.grid()

        # lettres & chiffres autour
        for i in range(8):
            Label(self.mainframe, text=chr(ord('A') + i), bg='white').grid(row=0, column=i + 1)
            Label(self.mainframe, text=str(8 - i), bg='white').grid(row=i + 1, column=0)

        # -------------------------------------------------------------
        # CANVAS REDIMENSIONNÉ POUR LE PLATEAU
        # -------------------------------------------------------------
        self.canvas = Canvas(self.mainframe, width=board_width, height=board_height, bg="black")
        self.canvas.grid(row=1, column=1, rowspan=8, columnspan=8)

        # fond du plateau redimensionné
        bg = Image.open("img/plateau.png").resize((board_width, board_height))
        self.bg_photo = ImageTk.PhotoImage(bg)
        self.canvas.create_image(board_width/2, board_height/2, image=self.bg_photo)

        self.pieces_list = []

        # affichage initial
        self.update_board()

        # boucle du jeu
        self.root.after(1000, self.jouer)

    # -------------------------------------------------------------
    def get_x_from_col(self, col): return board_width/8*col + board_width/16
    def get_y_from_row(self, row): return board_height/8*row + board_height/16

    def display_piece(self, piece, col, row):
        img = self.img_dict[piece]
        pid = self.canvas.create_image(self.get_x_from_col(col), self.get_y_from_row(row), image=img)
        self.pieces_list.append(pid)

    # -------------------------------------------------------------
    def update_board(self):
        for p in self.pieces_list:
            self.canvas.delete(p)
        self.pieces_list.clear()

        row = 0
        col = 0

        for c in self.board.board_fen():
            if c.isdigit():
                col += int(c)
            elif c == "/":
                row += 1
                col = 0
            else:
                self.display_piece(c, col, row)
                col += 1

    # -------------------------------------------------------------
    def jouer(self):

        if self.board.is_game_over():
            res = self.board.result()
            msg = {"1-0": "Les blancs ont gagné !", "0-1": "Les noirs ont gagné !"}.get(res, "Égalité !")
            self.canvas.create_text(board_width/2, board_height/2, text=msg, fill="red", font=("Arial", 32))
            return

        if self.board.turn == WHITE:
            coup = self.Joueur_Blanc.coup()
        else:
            coup = self.Joueur_Noir.coup()

        try:
            self.board.push_san(coup)
        except:
            print("Coup invalide:", coup)
            return

        self.update_board()
        self.root.after(100, self.jouer)


# ----------------------------------------------------------------------
# Exemple d'utilisation (humain vs AI aléatoire)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = Tk()
    board = Board()

    J_Blanc = JoueurHumain(board)
    J_Noir = JoueurAleatoire(board)  # AI aléatoire

    Chess_UI(root, board, J_Blanc, J_Noir)
    root.mainloop()
