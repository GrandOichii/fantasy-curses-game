import curses
from Game import GameWindow
from Configuraion import ConfigFile
import sys
import os
import curses

os.environ.setdefault('ESCDELAY', '25')

config_path = 'settings.config'

def main(stdscr):
    curses.curs_set(0)
    gw = GameWindow(stdscr, ConfigFile(config_path))
    if '-d' in sys.argv: gw.debug = True
    gw.start()

curses.wrapper(main)