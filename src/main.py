from Game import Game
import sys
import os

os.environ.setdefault('ESCDELAY', '25')

game = Game('saves', 'assets', 'assets/rooms', 'assets/map.map')
if '-d' in sys.argv: game.debug = True
game.start()