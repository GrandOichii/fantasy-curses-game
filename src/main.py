from Game import Game
import sys

game = Game('saves')
if '-d' in sys.argv: game.debug = True
game.start()