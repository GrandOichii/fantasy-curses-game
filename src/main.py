from Game import Game
from Configuraion import ConfigFile
import sys
import os

os.environ.setdefault('ESCDELAY', '25')

config_path = 'settings.config'

# game = Game('saves', 'assets', 'assets/map_test/', 'assets/map_test/map.map', starting_room='room5')
# game = Game('saves', 'assets', 'assets/rooms/', '')
game = Game(ConfigFile(config_path))
if '-d' in sys.argv: game.debug = True
game.start()