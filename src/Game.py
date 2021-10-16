import curses
import curses.textpad as textpad

import os

from Menu import Menu, Button, ActionButton

class Game:
    def __init__(self, saves_path, assets_path):
        self.debug = False
        self.assets_path = assets_path
        self.saves_path = saves_path

        self.create_folders()
        main_menu = Menu()
        main_menu.choice_symbol = '> '
        main_menu.title = 'Fantasy Curses Game'
        main_menu.text = 'This is a fantasy game made using python curses'

        settings_menu = Menu()
        settings_menu.choice_symbol = '> '
        settings_menu.title = 'Settings'
        settings_menu.text = 'Nothing here yet'

        credits_menu = Menu()
        credits_menu.choice_symbol = '> '
        credits_menu.title = 'Credits'
        credits_menu.text = 'https://github.com/GrandOichii/fantasy-curses-game'

        new_game_button = ActionButton('New game', main_menu, self.new_game_action)

        load_button = ActionButton('Load', main_menu, self.load_game_action)

        main_to_settings_button = Button('Settings', main_menu)
        main_to_settings_button.connect_to(settings_menu)

        main_to_credits_button = Button('Credits', main_menu)
        main_to_credits_button.connect_to(credits_menu)

        exit_button = ActionButton('Exit', main_menu, self.exit_action)

        back_to_main_button = Button('Back', settings_menu)
        back_to_main_button.connect_to(main_menu)
        credits_menu.add_button(back_to_main_button)

        self.current_menu = main_menu

    def create_folders(self):
        # create saves folder
        if not os.path.exists(self.assets_path):
            raise Exception('ERROR: No assets folder found')
        if not os.path.exists(self.saves_path):
            try:
                os.mkdir(self.saves_path)
            except Exception as ex:
                print('ERROR - Could not create saves folder')
                print(ex)
                input()
                exit()

    def count_saves(self):
        return len(os.listdir(self.saves_path))

    def start(self):
        curses.wrapper(self.main)

    def main(self, stdscr):
        self.stdscr = stdscr
        self.HEIGHT, self.WIDTH = self.stdscr.getmaxyx()
        self.menu_choice_id = 0

        # remove cursor
        curses.curs_set(0)

        # for testing purposes
        stdscr = curses.initscr()

        # init colors

        # initial display
        self.display_current_menu(1, 1)
        stdscr.refresh()

        # main game loop
        self.running = True
        while self.running:
            key = stdscr.getch()
            stdscr.clear()

            # keys
            if key in [81]: # Q
                self.running = False
            if key in [259]: # UP
                self.menu_choice_id -= 1
                if self.menu_choice_id < 0:
                    self.menu_choice_id = len(self.current_menu.buttons) - 1
            if key in [258]: # DOWN
                self.menu_choice_id += 1
                if self.menu_choice_id >= len(self.current_menu.buttons):
                    self.menu_choice_id = 0
            if key in [10]: # ENTER
                if not self.current_menu.buttons[self.menu_choice_id].leads_to:
                    if not isinstance(self.current_menu.buttons[self.menu_choice_id], ActionButton) :
                        self.message_box('This button doesn\'t do anything', ['Ok'])
                    else:
                        self.current_menu.buttons[self.menu_choice_id].click()
                else:
                    self.current_menu = self.current_menu.buttons[self.menu_choice_id].leads_to
                    self.menu_choice_id = 0

            if self.running:
                if self.debug: self.addstr(0, 0, f'KEY: |{key}|')
                self.display_current_menu(1, 1)
                stdscr.refresh()

    def addstr(self, ypos, xpos, message):
        self.stdscr.addstr(ypos, xpos, message)

    def message_box(self, message, choices, height=-1, width=-1, additional_lines=[]):
        # restrict the min and max width of message box
        if len(choices) == 0 or len(choices) > 3:
            raise Exception(f'MESSAGE_BOX ERROR: choices length can\'t be {len(choices)}')
        choice_id = 0
        done = False

        # set max min values
        max_width = self.WIDTH - 2

        # calculate values
        choices_len = (len(choices) + 1) * 2
        for choice in choices:
            choices_len += len(choice)
        if height == -1:
            height = 6 + len(additional_lines)
        if width == -1:
            width = max(choices_len, len(message) + 4)
            max_add_len = 0
            for add in additional_lines:
                max_add_len = max(max_add_len, len(add))
            max_add_len += 4
            width = max(width, max_add_len)
            width = min(max_width, width)
        ypos = (self.HEIGHT - height) // 2
        xpos = (self.WIDTH - width) // 2
        
        # print the message box itself
        win = curses.newwin(height + 2, width + 2, ypos - 1, xpos - 1)
        textpad.rectangle(win, 0, 0, height, width + 1)
        win.addstr(2, 3, message)
        win.keypad(1)
        for i in range(len(additional_lines)):
            win.addstr(3 + i, 3, additional_lines[i])
        pos = 3
        for i in range(len(choices)):
            if i == choice_id:
                win.addstr(height - 2, pos - 1, f'[{choices[i]}]')
            else:
                win.addstr(height - 2, pos, choices[i])
            pos += len(choices[i]) + 2


        while not done:
            key = win.getch()
            win.addstr(height - 2, 1, ' ' * width)
            win.refresh()
            if key in [260]: # LEFT
                choice_id -= 1
                if choice_id < 0:
                    choice_id = len(choices) - 1
            if key in [261]: # RIGHT
                choice_id += 1
                if choice_id >= len(choices):
                    choice_id = 0
            pos = 3
            for i in range(len(choices)):
                if i == choice_id:
                    win.addstr(height - 2, pos - 1, f'[{choices[i]}]')
                else:
                    win.addstr(height - 2, pos, choices[i])
                pos += len(choices[i]) + 2
            if key == 10:
                done = True
            if self.debug: win.addstr(0, 0, f'KEY: |{key}|')
        win.clear()
        win.refresh()
        return choices[choice_id]

    def display_menu(self, menu, y, x):
        self.addstr(y, x, menu.title)
        self.addstr(y + 2, x, menu.text)
        for i in range(len(menu.buttons)):
            self.addstr(y + 4 + i, x + len(menu.choice_symbol), menu.buttons[i].text)
            if i == self.menu_choice_id:
                self.addstr(y + 4 + i, x, menu.choice_symbol)

    def display_current_menu(self, y, x):
        self.display_menu(self.current_menu, y, x)
            
    def exit_action(self):
        self.running = False

    def new_game_action(self):
        self.stdscr.clear()
        enstr = 'Enter your character\'s name (press ESC to cancel): '
        max_name_len = 20
        min_name_len = 3
        self.addstr(1, 1, f'{enstr}')
        self.addstr(1, 1 + len(enstr), '_' * max_name_len)
        done = False
        name = ''
        while not done:
            key = self.stdscr.getch()
            if self.debug: self.addstr(0, 0, f'KEY: |{key}|')
            if (key >= 97 and key <= 122) or (key >= 65 and key <= 90) or key in [32]: # from a to z, from A to Z, SPACE
                if len(name) >= max_name_len:
                    self.message_box(f'Maximum length of character is {max_name_len}', ['Ok'])
                else:
                    name += chr(key)
            # too slow for some reason
            if key in [27]: # ESC
                cancel_result = self.message_box('Cancel character creation?', ['No', 'Yes'])
                if cancel_result == 'Yes':
                    self.stdscr.clear()
                    return
            if key in [127, 8]: # BACKSPACE
                if len(name) > 0:
                    name = name[:-1]
                else:
                    cancel_result = self.message_box('Cancel character creation?', ['No', 'Yes'])
                    if cancel_result == 'Yes':
                        self.stdscr.clear()
                        return
            if key in [10]: # ENTER
                if len(name) < min_name_len:
                    self.message_box(f'The name has to be at least {min_name_len} characters long!', ['Ok'])
                else:
                    done = True
            if not done:
                placeholder = '_' * (max_name_len - len(name))
                self.addstr(1, 1 + len(enstr), f'{name}{placeholder}')
        class_result = self.message_box('Choose your character class:', ['Warrior', 'Mage', 'Thief'])
        if self.message_box('Is this ok?',  ['Yes', 'No'], additional_lines=[f'Name: {name}', f'Class: {class_result}'],) == 'No':
            self.new_game_action()
            return
        # create character with name and class_result
        self.stdscr.clear()

    def load_game_action(self):
        if self.count_saves() == 0:
            self.message_box('No save files detected!', ['Ok'])
            return
        self.message_box('To be implemented', ['Ok'])



