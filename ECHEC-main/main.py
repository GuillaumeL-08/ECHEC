from chess import Board
from canvas_tkinter import *   # BUG FIX: était "from img.canvas_tkinter import *"
from ia_tree import TreeIA

board = Board()
root = Tk()
root.title("Echecs")

ia_blanc = TreeIA(depth=4, enable_learning=True)  # Humain joue les blancs
ia_noir = TreeIA(depth=4, enable_learning=True)   # IA joue les noirs

c = Chess_UI(root, board, ia_blanc, ia_noir)

root.mainloop()