from Game import Game
from Configuraion import ConfigFile
import sys
import os

os.environ.setdefault('ESCDELAY', '25')

config_path = 'settings.config'

game = Game(ConfigFile(config_path))
if '-d' in sys.argv: game.debug = True
game.start()