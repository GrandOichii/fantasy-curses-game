import curses
import Game
from Configuraion import ConfigFile
import sys
import os
import curses
import logging


os.environ.setdefault('ESCDELAY', '25')

config_path = 'settings.config'

def main(stdscr):
    curses.curs_set(0)
    gw = Game.GameWindow(stdscr, ConfigFile(config_path))
    if '-d' in sys.argv: logging.basicConfig(filename='gamelog.log', level=logging.DEBUG)
    gw.start()

curses.wrapper(main)