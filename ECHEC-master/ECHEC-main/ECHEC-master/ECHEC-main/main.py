from chess import Board
from canvas_tkinter import *   # BUG FIX: était "from img.canvas_tkinter import *"
from simple_ia import SimpleIA

board = Board()
root = Tk()
root.title("Echecs")

ia_blanc = SimpleIA()   # Humain joue les blancs
ia_noir = SimpleIA()   # IA joue les noirs

c = Chess_UI(root, board, ia_blanc, ia_noir)

root.mainloop()