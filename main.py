from chess import *
from canvas_tkinter import *
#import ... as IA1
#import ... as IA2
from ia_tree import TreeIA

"""
Décommentez les imports pour y mettre votre fichier d'IA
"""

board = Board()
root = Tk()
root.title("Echecs")

"""
Rajoutez le nom de votre fichier pour jouer à votre Jeu et en entrée de la fonction classe Chess_UI
"""

ia_blanc = None              # Humain joue les blancs
ia_noir = TreeIA(board, depth=3)  # IA joue les noirs

c = Chess_UI(root, board, ia_blanc, ia_noir)

root.mainloop()
