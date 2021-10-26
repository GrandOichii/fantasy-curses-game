from Game import Game
import sys
import os

os.environ.setdefault('ESCDELAY', '25')

game = Game('saves', 'assets', 'assets/map_test/', 'assets/map_test/map.map', starting_room='room5')
if '-d' in sys.argv: game.debug = True
game.start()