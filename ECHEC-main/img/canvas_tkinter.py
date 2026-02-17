from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
from random import randint
from chess import *
import chess
from time import sleep
from human_controller import HumanController

# global vars
board_width = 1024
board_height = 1024


class Chess_UI:
    """
    Gère l'affichage du plateau d'échec et  gère la board de la librairie Chess
    ...
    Attributs 
    ----------
    root : Tk
        L'interface Tkinter
    board : Board
        Le plateau d'échec
    Joueur_Blanc : À definir
        L'IA du Joueur Blanc
    Jouer_Noir : À définir
        L'IA du Joueur Noir
    history_white & history_black : list
        Donne la liste des coups joué par les blancs et les noirs

    Méthodes
    ----------
    get_x_from_col(self, col) -> float
        Donne la valeur des coordonnées pour les colonnes
    get_y_from_row(self, row) -> float
        Donne la valuer des coordonnées pour les lignes
    display_piece(self, piece, col, row) -> None
        Affiche les pièces sur l'échiquier et les stockes dans une liste
    update_board() -> None
        Met à jour le plateau et met en place le coup suivant
    update_history_white(self, entry) -> None
        Met à jour la liste des coups des blancs
    update_history_black(self, entry) -> None
        Met à jour la liste des coups des noirs
    jouer(self) -> int
        Permet aux joueurs de jouer leur coups chacun leur tour
    """
    def __init__(self, root:Tk, board:Board, J_Blanc, J_Noir):  
        """
        Construit le plateau, définit les images des pièces. 
        Initialise les variables de jeu et lance la première partie.
        """
        #Définition des images pour les pièces
        self.img_dict = {
            'p': ImageTk.PhotoImage(Image.open('ECHEC-main/img/pion_noir.png').resize((100, 100))),
            'b': ImageTk.PhotoImage(Image.open('ECHEC-main/img/fou_noir.png').resize((100, 100))),
            'q': ImageTk.PhotoImage(Image.open('ECHEC-main/img/reine_noire.png').resize((100, 100))),
            'k': ImageTk.PhotoImage(Image.open('ECHEC-main/img/roi_noir.png').resize((100, 100))),
            'n': ImageTk.PhotoImage(Image.open('ECHEC-main/img/cavalier_noir.png').resize((100, 100))),
            'r': ImageTk.PhotoImage(Image.open('ECHEC-main/img/tour_noire.png').resize((100, 100))),
            'P': ImageTk.PhotoImage(Image.open('ECHEC-main/img/pion_blanc.png').resize((100, 100))),
            'B': ImageTk.PhotoImage(Image.open('ECHEC-main/img/fou_blanc.png').resize((100, 100))),
            'Q': ImageTk.PhotoImage(Image.open('ECHEC-main/img/reine_blanche.png').resize((100, 100))),
            'K': ImageTk.PhotoImage(Image.open('ECHEC-main/img/roi_blanc.png').resize((100, 100))),
            'N': ImageTk.PhotoImage(Image.open('ECHEC-main/img/cavalier_blanc.png').resize((100, 100))),
            'R': ImageTk.PhotoImage(Image.open('ECHEC-main/img/tour_blanche.png').resize((100, 100))),
        }
        self.root = root
        self.board = board
        self.Joueur_Blanc = J_Blanc
        self.Joueur_Noir = J_Noir
        # True si le camp est contrôlé par un humain (J_Blanc ou J_Noir == None)
        self.human_white = (J_Blanc is None)
        self.human_black = (J_Noir is None)
        self.mainframe = ttk.Frame(self.root)
        self.mainframe.grid()
        #Met les numéros et les lettres autour de l'échiquier 
        for i in range(8):
            label = Label(self.mainframe, text=chr(ord('A') + i), bg='white')
            label.grid(row=0, column=i + 1, sticky=(S))
            label = Label(self.mainframe, text=chr(ord('1') + i), bg='white')
            label.grid(row=i + 1, column=0, sticky=(E))

        #Affiche la liste déroulante de l'historique des mouvements
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
        self.bg_img = Image.open('ECHEC-main/img/plateau.png')
        self.bg_photo = ImageTk.PhotoImage(self.bg_img)
        self.canvas.create_image(board_width / 2, board_height / 2, image=self.bg_photo)
        
        self.pieces_list = []

        # Contrôleur pour les interactions humaines (clics)
        self.human_controller = HumanController(
            board=self.board,
            canvas=self.canvas,
            root=self.root,
            human_white=self.human_white,
            human_black=self.human_black,
            update_board_cb=self.update_board,
        )

        # On permet au HumanController de déclencher le tour IA après un coup humain
        # en lui donnant une référence vers self.jouer via son callback interne.
        self.human_controller._jouer_after_human = self.jouer

        self.update_board() #Affichage sur l'interface
        
        # Démarrer le premier tour de jeu après un court délai
        self.root.after(1000, self.jouer)
        

    # takes a col number as parameter (between 0 and 7). Returns the matching x coordinate (center of the cell) in the canvas
    def get_x_from_col(self, col:int) -> float:
        """
        prend un numéro de colonne comme paramètre (entre 0 et 7). 
        Renvoie la coordonnée x correspondante (centre de la cellule) dans le canevas.
        """
        if col < 0 or col > 7:
            raise ValueError(col)
        return col * (board_width / 8) + (board_width / 16)

    # takes a row number as parameter (between 0 and 7). Returns the matching y coordinate (center of the cell) in the canvas
    def get_y_from_row(self, row:int) -> float:
        """
        prend un numéro de ligne comme paramètre (entre 0 et 7). 
        Renvoie la coordonnée y correspondante (centre de la cellule) dans le canevas.
        """
        if row < 0 or row > 7:
            raise ValueError(row)
        return row * (board_height / 8) + (board_height / 16)

    def display_piece(self, piece, col, row):
        """
        Affiche une pièce sur l'échiquier à la position spécifiée.
        La pièce est ajoutée à la liste des pièces pour pouvoir être effacée plus tard.
        """
        x = self.get_x_from_col(col)
        y = self.get_y_from_row(row)
        img = self.img_dict[piece.symbol()]
        piece_img = self.canvas.create_image(x, y, image=img)
        self.pieces_list.append(piece_img)

    def update_board(self):
        """
        Met à jour l'affichage de l'échiquier en effaçant les pièces actuelles 
        et en affichant les nouvelles positions.
        """
        # Effacer toutes les pièces actuelles
        for piece_img in self.pieces_list:
            self.canvas.delete(piece_img)
        self.pieces_list.clear()
        
        # Afficher les nouvelles positions
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is not None:
                col = chess.square_file(square)
                row = 7 - chess.square_rank(square)  # Inverser pour l'affichage
                self.display_piece(piece, col, row)
        
        # Mettre à jour l'historique si nécessaire (simplifié pour éviter les erreurs)
        if len(self.board.move_stack) > 0:
            try:
                last_move = self.board.move_stack[-1]
                temp_board = self.board.copy()
                temp_board.pop()
                move_str = temp_board.san(last_move)
                
                if self.board.turn == chess.WHITE:
                    self.update_history_black(move_str)
                else:
                    self.update_history_white(move_str)
            except:
                # En cas d'erreur, ignorer l'historique pour ne pas bloquer le jeu
                pass
        
        # Lancer le prochain coup si ce n'est pas à un humain de jouer
        self.root.after(500, self.jouer)

    def update_history_white(self, entry):
        self.history_white.append(entry)
        self.history_white_var.set(self.history_white)

    def update_history_black(self, entry):
        self.history_black.append(entry)
        self.history_black_var.set(self.history_black)

    def jouer(self):

        #Vérification de la victoire
        if self.board.is_game_over():
            res = self.board.result()
            if res == "1-0":
                res = "Les blancs ont gagné !"
            elif res == "0-1":
                res = "Les noir ont gagné !"
            else:
                res = "Egalité !"

            # Notifier les IAs que la partie est terminée pour l'apprentissage
            if hasattr(self.Joueur_Blanc, 'end_game'):
                self.Joueur_Blanc.end_game(self.board.result(), self.board)
            if hasattr(self.Joueur_Noir, 'end_game'):
                self.Joueur_Noir.end_game(self.board.result(), self.board)

            # Afficher les statistiques d'apprentissage si disponibles
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
        

        #Tour d'un des joueurs (uniquement IA côté Chess_UI)
        if self.board.turn == WHITE:
            # Tour des blancs
            if self.human_white:
                # C'est un humain : Chess_UI ne joue pas, HumanController s'en charge
                return
            self.board.push_san(self.Joueur_Blanc.coup(self.board))
        else:
            # Tour des noirs
            if self.human_black:
                # C'est un humain : Chess_UI ne joue pas, HumanController s'en charge
                return
            self.board.push_san(self.Joueur_Noir.coup(self.board))
            
        self.update_board() #Mise à jour de l'échiquier
