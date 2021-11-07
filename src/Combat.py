import curses
from curses.textpad import rectangle

import Utility

from gamelib.Entities import Player, Enemy

class CombatEncounter:
    def __init__(self, attacker, defender, distance, height, width):
        self.HEIGHT = height
        self.WIDTH = width

        self.calc_height_width()

        self.window = None

        self.entities = [attacker, defender]
        self.turn_id = 0
        self.combat_log = []
        self.cl_page = 0
        self.add_to_combat_log(f'{attacker.name} attacks {defender.name}!')
        self.distance = int(distance)

        self.player_id = -1
        for i in range(len(self.entities)):
            if isinstance(self.entities[i], Player):
                self.player_id = i
        if self.player_id == -1:
            raise Exception('ERR: in encounter to player was found')

    def calc_height_width(self):
        self.box_height = self.HEIGHT - 2
        self.box_width = self.WIDTH // 3
        
        self.middle_height = self.HEIGHT - 2
        self.middle_width = self.WIDTH - self.box_width * 2

        self.combat_log_window_height = self.HEIGHT * 3 // 8
        self.combat_log_window_width = self.middle_width - 1
        self.combat_log_message_width = self.combat_log_window_width - 3

        self.cl_limit = self.combat_log_window_height - 2

    def draw_borders(self, w):
        w.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def initial_draw(self):
        self.draw_borders(self.window)

        # player static info
        self.draw_borders(self.player_window)
        self.player_window.addstr(0, 1, self.get_player().name)

        # enemy static info
        self.draw_borders(self.enemy_window)
        self.enemy_window.addstr(0, 1, self.get_enemy().name)

        # combat info
        self.draw_borders(self.combat_info_window)
        self.combat_info_window.addstr(0, 1, 'Combat info')
        self.combat_info_window.addstr(3, 1, ' DISTANCE: ')

        self.draw()

    def draw(self):
        # display distance
        self.combat_info_window.addstr(3, 12, str(self.distance))
        self.draw_combat_log()
        self.window.refresh()
        self.player_window.refresh()
        self.enemy_window.refresh()
        self.combat_info_window.refresh()
        self.combat_log_window.refresh()

    def draw_combat_log(self):
        self.combat_log_window.clear()
        self.draw_borders(self.combat_log_window)
        self.combat_log_window.addstr(0, 1, 'Combat log')
        y = 0
        first = 0
        last = len(self.combat_log) - 1
        if len(self.combat_log) > self.cl_limit:
            first = self.cl_page
            last = self.cl_page + self.cl_limit - 1
        for i in range(first, last + 1):
            self.combat_log_window.addstr(1 + y, 1, self.combat_log[i])
            y += 1
        for i in range(self.cl_limit):
            self.combat_log_window.addch(1 + i, self.combat_log_message_width, curses.ACS_VLINE)
        if len(self.combat_log) > self.cl_limit:
            if self.cl_page != 0:
                self.combat_log_window.addch(1, self.combat_log_message_width, curses.ACS_UARROW)
            if self.cl_page !=  len(self.combat_log) - self.cl_limit:
                self.combat_log_window.addch(self.combat_log_window_height - 2, self.combat_log_message_width, curses.ACS_DARROW)

    def start(self):
        self.window = curses.newwin(self.HEIGHT, self.WIDTH, 0, 0)
        self.combat_info_window = curses.newwin(self.middle_height - self.combat_log_window_height, self.middle_width - 1, 1, self.box_width + 1)
        self.combat_log_window = curses.newwin(self.combat_log_window_height, self.combat_log_window_width, self.HEIGHT - self.combat_log_window_height - 1, self.box_width + 1)
        self.player_window = curses.newwin(self.box_height, self.box_width, 1, 1)
        self.enemy_window = curses.newwin(self.box_height, self.box_width, 1, self.WIDTH - self.box_width)
        self.initial_draw()
        self.main_loop()
       
    def main_loop(self):
        while True:
            key = self.window.getch()
            
            # ONLY FOR DEBUG, MAY BREAK
            if key == 81: # Q
                break
            if key == 32: # SPACE
                self.add_to_combat_log('Lorem ipsum ibsolares she will never miss me')

            if key == 60: # <
                if len(self.combat_log) > self.cl_limit:
                    self.cl_page -= 1
                    if self.cl_page < 0:
                        self.cl_page = 0
            if key == 62: # >
                if len(self.combat_log) > self.cl_limit:
                    self.cl_page += 1
                    if self.cl_page > len(self.combat_log) - self.cl_limit:
                        self.cl_page = len(self.combat_log) - self.cl_limit
            self.draw()

    def add_to_combat_log(self, message):
        message = '- ' + message
        self.combat_log += Utility.str_smart_split(message, self.combat_log_message_width)
        if len(self.combat_log) > self.cl_limit:
            self.cl_page = len(self.combat_log) - self.cl_limit

    def get_player(self):
        return self.entities[self.player_id]

    def get_enemy(self):
        return self.entities[1 - self.player_id]
