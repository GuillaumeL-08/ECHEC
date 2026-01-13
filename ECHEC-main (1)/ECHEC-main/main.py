from chess import *
from img.canvas_tkinter import *
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

ia_blanc = None    # IA joue les blancs
ia_noir = TreeIA(depth=4, enable_learning=True)    # IA joue les noirs

c = Chess_UI(root, board, ia_blanc, ia_noir)

root.mainloop()
