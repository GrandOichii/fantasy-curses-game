import curses
import curses.textpad as textpad
import json

import os
import gamelib.SaveFile as SaveFile

from ui.Menu import Menu
from ui.Buttons import Button, ActionButton

from gamelib.Entities import Player

import Utility
import gamelib.Room as Room
import gamelib.Items as Items

class Game:
    def __init__(self, saves_path, assets_path, rooms_path, map_path):
        self.debug = False
        self.assets_path = assets_path
        self.saves_path = saves_path
        self.rooms_path = rooms_path
        self.map_path = map_path
        self.max_name_len = 20
        self.starting_room = 'index'


        self.create_folders()
        self.main_menu = Menu()
        self.main_menu.choice_symbol = '> '
        self.main_menu.title = 'Fantasy Curses Game'
        self.main_menu.text = 'This is a fantasy game made using python curses'

        settings_menu = Menu()
        settings_menu.choice_symbol = '> '
        settings_menu.title = 'Settings'
        settings_menu.text = 'Nothing here yet'

        credits_menu = Menu()
        credits_menu.choice_symbol = '> '
        credits_menu.title = 'Credits'
        credits_menu.text = 'https://github.com/GrandOichii/fantasy-curses-game'

        ActionButton('new_game_button', 'New game', self.main_menu, self.new_game_action)

        ActionButton('load_button', 'Load', self.main_menu, self.load_game_action)

        main_to_settings_button = Button('settings_button', 'Settings', self.main_menu)
        main_to_settings_button.connect_to(settings_menu)

        main_to_credits_button = Button('credits_button', 'Credits', self.main_menu)
        main_to_credits_button.connect_to(credits_menu)

        ActionButton('exit_button', 'Exit', self.main_menu, self.exit_action)

        back_to_main_button = Button('back_to_main_button', 'Back', settings_menu)
        back_to_main_button.connect_to(self.main_menu)
        credits_menu.add_button(back_to_main_button)

        self.current_menu = self.main_menu

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

    def start(self):
        curses.wrapper(self.main)

    def draw_borders(self, w):
        w.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def main(self, stdscr):
        if self.debug: self.draw_borders(stdscr)
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
                if self.debug: self.draw_borders(stdscr)
                stdscr.refresh()

    def addstr(self, ypos, xpos, message):
        self.stdscr.addstr(ypos, xpos, message)

    def display_dialog(self, message, replies):
        width = self.window_width - 2
        height = self.window_height // 2

        lines = Utility.str_smart_split(message, width - 2)
        name = '???'
        if '_say_name' in self.env_vars:
            name = self.get_env_var('_say_name')


        w = curses.newwin(height - 1, width, height + 1, 2)
        self.draw_borders(w)
        w.keypad(1)
        w.addstr(0, 1, name)

        for i in range(len(lines)):
            w.addstr(1 + i, 1, lines[i])
        w.addch(height - len(replies) - 3, 0, curses.ACS_LTEE)
        w.addch(height - len(replies) - 3, width - 1, curses.ACS_RTEE)
        for i in range(width - 2):
            w.addch(height - len(replies) - 3, 1 + i, curses.ACS_HLINE)
        w.addstr(height - len(replies) - 2, 1, '> ')
        for i in range(len(replies)):
            w.addstr(height - len(replies) - 2 + i, 3, replies[i])
        w.refresh()
        choice_i = 0
        while True:
            key = w.getch()
            if key == 259: # UP
                choice_i -= 1
                if choice_i < 0: choice_i = len(replies) - 1
            if key == 258: # DOWN
                choice_i += 1
                if choice_i >= len(replies): choice_i = 0
            if key == 10: # ENTER
                break

            for i in range(len(replies)):
                if i == choice_i:
                    w.addstr(height - len(replies) - 2 + i, 1, '> ')
                else:    
                    w.addstr(height - len(replies) - 2 + i, 1, '  ')
        return replies[choice_i]

    def message_box(self, message, choices, ypos=-1, xpos=-1, height=-1, width=-1, additional_lines=[]):
        # restrict the min and max width of message box
        if len(choices) == 0 or len(choices) > 3:
            raise Exception(f'MESSAGE_BOX ERROR: choices length can\'t be {len(choices)}')
        choice_id = 0
        done = False

        # if possible break up the messages
        if width != -1 and len(additional_lines) == 0:
            lines = Utility.str_smart_split(message, width - 6)
            if len(lines) != 1:
                message = lines[0]
                lines.pop(0)
                additional_lines = lines

        # set max min values
        max_width = self.WIDTH - 2

        # calculate values
        choices_len = (len(choices) + 1) * 2
        for choice in choices:
            choices_len += len(choice)
        if width == -1:
            width = max(choices_len, len(message) + 4)
            max_add_len = 0
            for add in additional_lines:
                max_add_len = max(max_add_len, len(add))
            max_add_len += 4
            width = max(width, max_add_len)
            width = min(max_width, width)
    
        if height == -1:
            height = 6 + len(additional_lines)

        if ypos == -1:
            ypos = (self.HEIGHT - height) // 2
        if xpos == -1:
            xpos = (self.WIDTH - width) // 2
        
        # print the message box itself
        win = curses.newwin(height + 1, width + 2, ypos - 1, xpos)
        self.draw_borders(win)

        # textpad.rectangle(win, 0, 0, height, width + 1)
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
            if key == 260: # LEFT
                choice_id -= 1
                if choice_id < 0:
                    choice_id = len(choices) - 1
            if key == 261: # RIGHT
                choice_id += 1
                if choice_id >= len(choices):
                    choice_id = 0
            if 'Cancel' in choices and key == 27: # ESC
                win.clear()
                win.refresh()
                return 'Cancel'
            pos = 3
            for i in range(len(choices)):
                if i == choice_id:
                    win.addstr(height - 2, pos - 1, f'[{choices[i]}]')
                else:
                    win.addstr(height - 2, pos, choices[i])
                pos += len(choices[i]) + 2
            if key == 10:
                done = True
            self.draw_borders(win)
            if self.debug: win.addstr(0, 0, f'KEY: |{key}|\t{height}; {width}')
        win.clear()
        win.refresh()
        return choices[choice_id]

    def prompt_display(self, message):
        self.addstr(11, self.window_width + 11, message)
        self.stdscr.refresh()
        key = self.stdscr.getch()
        self.addstr(11, self.window_width + 11, ' ' * (self.WIDTH - self.window_width - 11))
        self.stdscr.refresh()
        return key

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
        min_name_len = 3
        self.addstr(1, 1, f'{enstr}')
        self.addstr(1, 1 + len(enstr), '_' * self.max_name_len)
        done = False
        name = ''
        while not done:
            key = self.stdscr.getch()
            if self.debug: self.addstr(0, 0, f'KEY: |{key}|')
            if (key >= 97 and key <= 122) or (key >= 65 and key <= 90) or key in [32]: # from a to z, from A to Z, SPACE
                if len(name) >= self.max_name_len:
                    self.message_box(f'Maximum length of character is {self.max_name_len}', ['Ok'])
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
                placeholder = '_' * (self.max_name_len - len(name))
                self.addstr(1, 1 + len(enstr), f'{name}{placeholder}')
        class_result = self.message_box('Choose your character class:', ['Warrior', 'Mage', 'Thief'])
        if self.message_box('Is this ok?',  ['Yes', 'No'], additional_lines=[f'Name: {name}', f'Class: {class_result}']) == 'No':
            self.new_game_action()
            return
        
        # create character with name and class_result
        class_result = class_result.lower()
        player = Player()
        player.name = name
        data = json.loads(open('assets/class_schemas.json').read())
        if not class_result in data:
            raise Exception(f'ERR: Class {class_result} not found in assets')
        player.load_class(data[class_result], 'assets/items.json')
        already_exists = SaveFile.save_file_exists(self.saves_path, player.name)
        if already_exists and self.message_box(f'File with name {player.name} already exists, override?', ['No', 'Yes']) == 'No':
            self.stdscr.clear()
            self.new_game_action()
            return
        SaveFile.save(player, self.starting_room, self.saves_path)
        self.stdscr.clear()
        self.load_character(player.name)

    def load_game_action(self):
        if SaveFile.count_saves(self.saves_path) == 0:
            self.message_box('No save files detected!', ['Ok'])
            return
        save_desc, corrupt_files = SaveFile.save_descriptions(self.saves_path)
        for cor in corrupt_files:
            if self.message_box(f'Character {cor} seems to be corrupt, delete file?', ['No', 'Yes']) == 'Yes':
                SaveFile.delete_save_file(cor, self.saves_path)

        ch_names = SaveFile.character_names(self.saves_path)
        self.menu_choice_id = 0
        self.load_menu = Menu()
        self.load_menu.title = 'Load'
        self.load_menu.choice_symbol = '> '
        self.load_menu.text = 'Choose a save file:'
        for i in range(len(save_desc)):
            ActionButton(f'load_{ch_names[i]}_button', save_desc[i], self.load_menu, self.load_character_pick_action)
        button = Button('back_to_main_button', 'Back', self.load_menu)
        button.connect_to(self.main_menu)
        self.current_menu = self.load_menu

    def load_character_pick_action(self):
        name = SaveFile.character_names(self.saves_path)[self.menu_choice_id]
        response = self.message_box(f'Load character {name}?', ['Load', 'Delete', 'Cancel'])
        if response == 'Cancel':
            return
        if response == 'Load':
            self.load_character(name)
        if response == 'Delete' and self.message_box(f'Delete character {name}? (Permanent)', ['No', 'Yes']) == 'Yes':
            SaveFile.delete_save_file(name, self.saves_path)
            self.load_menu.remove_button_with_name(f'load_{name}_button')
            
    def load_character(self, character_name):
        # try:
        data = SaveFile.load(character_name, self.saves_path)
        if data == -1:
            raise Exception(f'ERR: save file of character with name {character_name} not found in {self.saves_path}')
        self.player = Player.from_json(data['player'])
        self.env_vars = data['env_vars']
        game_room = Room.Room.by_name(data['room_name'], self.rooms_path, self.assets_path)
        self.player_y, self.player_x = game_room.player_spawn_y, game_room.player_spawn_x
        if 'player_y' in data:
            self.player_y = data['player_y']
        if 'player_x' in data:
            self.player_x = data['player_x']
        # except Exception as ex:
        #     if self.debug: raise ex
        #     if self.message_box(f'Character {character_name} seems to be corrupt, delete file?', ['No', 'Yes']) == 'Yes':
        #         SaveFile.delete_save_file(character_name, self.saves_path)
        #         self.load_menu.remove_button_with_name(f'load_{character_name}_button')
        #     return
            
        self.stdscr.clear()

        # set some values
        self.window_height = self.HEIGHT * 5 // 6
        if self.window_height % 2 == 0: self.window_height -= 1
        self.window_width = self.WIDTH - self.max_name_len - 8

        self.window_width -= 1

        # permanent display
        self.tile_window = curses.newwin(self.window_height, self.window_width, 0, 1)
        self.draw_borders(self.tile_window)

        self.tile_window.keypad(1)
        self.display_info_ui()
        self.display_player_info()
        self.stdscr.refresh()

        self.mid_y = self.window_height // 2 
        self.mid_x = self.window_width // 2

        self.tile_window.addstr(self.mid_y, self.mid_x, '@')

        self.draw_tiles(self.player_y, self.player_x, game_room.visible_range, game_room)
        self.draw_torches(game_room)
        self.tile_window.addstr(self.mid_y, self.mid_x, '@')

        if '_load' in game_room.scripts:
            self.exec_script('_load', game_room.scripts)

        # main game loop
        while True:
            key = self.tile_window.getch()
            self.tile_window.clear()
            if key == 81 and self.message_box('Are you sure you want to quit? (Progress will be saved)', ['No', 'Yes'],width=self.window_width - 4, ypos=2, xpos=2) == 'Yes':
                SaveFile.save(self.player, game_room.name, self.saves_path, player_y=self.player_y, player_x=self.player_x, env_vars=self.env_vars)
                break
            # if self.debug and key == 126:
            if key == 126:
                command = self.get_terminal_command()
                self.exec_line(command, game_room.scripts)

            # movement management
            y_lim = game_room.height
            x_lim = game_room.width
            # North
            if key in [56, 259] and not self.player_y < 0 and not game_room.tiles[self.player_y - 1][self.player_x].solid:
                self.player_y -= 1
            # South
            if key in [50, 258] and not self.player_y >= y_lim and not game_room.tiles[self.player_y + 1][self.player_x].solid:
                self.player_y += 1
            # West
            if key in [52, 260] and not self.player_x < 0 and not game_room.tiles[self.player_y][self.player_x - 1].solid:
                self.player_x -= 1
            # East
            if key in [54, 261] and not self.player_x >= x_lim and not game_room.tiles[self.player_y][self.player_x + 1].solid:
                self.player_x += 1
            # NE
            if key in [117, 57] and not (self.player_y < 0 and not self.player_x >= x_lim) and not game_room.tiles[self.player_y - 1][self.player_x + 1].solid:
                self.player_y -= 1
                self.player_x += 1
            # NW
            if key in [121, 55] and not (self.player_y < 0 and self.player_x < 0) and not game_room.tiles[self.player_y - 1][self.player_x - 1].solid:
                self.player_y -= 1
                self.player_x -= 1
            # SW
            if key in [98, 49] and not (self.player_y >= y_lim and self.player_x < 0) and not game_room.tiles[self.player_y + 1][self.player_x - 1].solid:
                self.player_y += 1
                self.player_x -= 1
            # SE
            if key in [110, 51] and not (self.player_y >= y_lim and self.player_x >= x_lim) and not game_room.tiles[self.player_y + 1][self.player_x + 1].solid:
                self.player_y += 1
                self.player_x += 1
            # interact
            if key == 101: # e
                interactable_tiles = self.get_interactable_tiles(game_room, self.player_y, self.player_x)
                if len(interactable_tiles) == 0:
                    self.message_box('No tiles to interact with nearby!', ['Ok'],width=self.window_width - 4, ypos=2, xpos=2)
                else:
                    interact_key = self.prompt_display('Interact where?')
                    flag = False
                    i_tile = None
                    for o in interactable_tiles:
                        if interact_key in o[1]:
                            flag = True
                            i_tile = o[0]
                    if flag:
                        if isinstance(i_tile, Room.ChestTile):
                            self.interact_with_chest(i_tile)
                        if isinstance(i_tile, Room.HiddenTile) and isinstance(i_tile.actual_tile, Room.ChestTile):
                            self.interact_with_chest(i_tile.actual_tile)
                        if isinstance(i_tile, Room.ScriptTile):
                            self.exec_script(i_tile.script_name, game_room.scripts)
                        if isinstance(i_tile, Room.HiddenTile) and isinstance(i_tile.actual_tile, Room.ScriptTile):
                            self.exec_script(i_tile.actual_tile.script_name, game_room.scripts)
                    else:
                        a=1
                        # add to log history
            # open inventory
            if key == 105: # i
                self.open_inventory()
                
            tile = game_room.tiles[self.player_y][self.player_x]
            # check if is standing on a door
            if isinstance(tile, Room.DoorTile) and self.message_box(f'Use door?', ['No', 'Yes'], width=self.window_width - 4, ypos=2, xpos=2) == 'Yes':
                destination_room = tile.to
                door_code = tile.door_code
                self.set_env_var('last_door_code', door_code)
                game_room = Room.Room.by_name(destination_room, self.rooms_path, self.assets_path, door_code=door_code)
                self.player_y, self.player_x = game_room.player_spawn_y, game_room.player_spawn_x
                self.tile_window.clear()
                self.tile_window.refresh()
                if '_load' in game_room.scripts:
                    self.exec_script('_load', game_room.scripts)
                if '_enter' in game_room.scripts:
                    self.exec_script('_enter', game_room.scripts)
            if isinstance(tile, Room.PressurePlateTile) and self.get_env_var(tile.signal) in [None, False]:
                self.set_env_var(tile.signal, True)
            if isinstance(tile, Room.HiddenTile) and self.get_env_var(tile.signal) == True and isinstance(tile.actual_tile, Room.PressurePlateTile) and self.get_env_var(tile.actual_tile.signal) in [None, False]:
                self.set_env_var(tile.actual_tile.signal, True)

            self.draw_borders(self.tile_window)
            self.draw_tiles(self.player_y, self.player_x, game_room.visible_range, game_room)
            self.draw_torches(game_room)
            # last to display
            self.tile_window.addstr(self.mid_y, self.mid_x, '@')

            self.display_player_info()
            self.tile_window.refresh()
            self.stdscr.refresh()
            
        # end of method
        self.tile_window.clear()
        self.tile_window.refresh()
        self.stdscr.clear()
        self.stdscr.refresh()
        self.current_menu = self.main_menu

    def display_info_ui(self):
        s = '1234567891234567891234'
        self.addstr(1, self.window_width + 3, f'Name: {self.player.name}')
        self.addstr(2, self.window_width + 3, f'Class: {self.player.class_name}')
        self.addstr(4, self.window_width + 3, f'Health:          (   /   )') # left: 19
        self.addstr(5, self.window_width + 3, f'Mana:            (   /   )') # left: 21
        self.addstr(7, self.window_width + 3, f'STR:') # left: 22
        self.addstr(8, self.window_width + 3, f'DEX:') # left: 22
        self.addstr(9, self.window_width + 3, f'INT:') # left: 22
        self.addstr(11, self.window_width + 3, 'Prompt: ')
        self.stdscr.refresh()

    def display_player_info(self):
        health_info =  ' ' * (3 - len(str(self.player.health))) + f'{self.player.health}'
        self.addstr(4, self.window_width + 21, f'{health_info}')
        max_health_info =  ' ' * (3 - len(str(self.player.max_health))) + f'{self.player.max_health}'
        self.addstr(4, self.window_width + 25, f'{max_health_info}')
        self.addstr(4, self.window_width + 10, Utility.calc_pretty_bars(self.player.health, self.player.max_health, 10))
        
        mana_info =  ' ' * (3 - len(str(self.player.mana))) + f'{self.player.mana}'
        self.addstr(5, self.window_width + 21, f'{mana_info}')
        max_mana_info =  ' ' * (3 - len(str(self.player.max_mana))) + f'{self.player.max_mana}'
        self.addstr(5, self.window_width + 25, f'{max_mana_info}')
        self.addstr(5, self.window_width + 10, Utility.calc_pretty_bars(self.player.mana, self.player.max_mana, 10))

        str_info = ' ' * (3 - len(str(self.player.STR))) + f'{self.player.STR}'
        self.addstr(7, self.window_width + 7, f'{str_info}')
        dex_info = ' ' * (3 - len(str(self.player.DEX))) + f'{self.player.DEX}'
        self.addstr(8, self.window_width + 7, f'{dex_info}')
        int_info = ' ' * (3 - len(str(self.player.INT))) + f'{self.player.INT}'
        self.addstr(9, self.window_width + 7, f'{int_info}')

    def draw_torches(self, game_room):
        for i in range(game_room.height):
            for j in range(game_room.width):
                if isinstance(game_room.tiles[i][j], Room.TorchTile):
                    self.draw_tiles(i, j, game_room.tiles[i][j].visible_range, game_room)
                if isinstance(game_room.tiles[i][j], Room.HiddenTile) and self.get_env_var(game_room.tiles[i][j].signal) == True and isinstance(game_room.tiles[i][j].actual_tile, Room.TorchTile):
                    # !!! BIG ISSUE !!! either rework hidden tiles, or make a work-around
                    self.draw_tiles(i, j, game_room.tiles[i][j].actual_tile.visible_range, game_room)

    def draw_tiles(self, y, x, visible_range, game_room):
        mid_y = self.mid_y - self.player_y + y
        mid_x = self.mid_x - self.player_x + x
        for i in range(max(1, mid_y - visible_range), min(self.window_height - 1, mid_y + visible_range + 1)):
            for j in range(max (1, mid_x - visible_range), min(self.window_width - 1, mid_x + visible_range + 1)):
                if Utility.distance(i, j, mid_y, mid_x) < visible_range:
                    room_y = i + y - mid_y
                    room_x = j + x - mid_x
                    if room_y < 0 or room_x < 0 or room_y >= game_room.height or room_x >= game_room.width:
                        self.tile_window.addch(i, j, '#')
                    else:
                        if game_room.tiles[room_y][room_x].char == '!':
                            self.tile_window.addch(i, j, game_room.tiles[room_y][room_x].char, curses.A_BLINK)
                        else:
                            tile = game_room.tiles[room_y][room_x]
                            if isinstance(tile, Room.HiddenTile):
                                if self.get_env_var(tile.signal) == True:
                                    game_room.tiles[room_y][room_x].solid = game_room.tiles[room_y][room_x].actual_tile.solid
                                    game_room.tiles[room_y][room_x].interactable = game_room.tiles[room_y][room_x].actual_tile.interactable
                                    self.tile_window.addch(i, j, game_room.tiles[room_y][room_x].actual_tile.char)
                                else:
                                    game_room.tiles[room_y][room_x].solid = True
                                    game_room.tiles[room_y][room_x].interactable = False
                                    self.tile_window.addch(i, j, game_room.tiles[room_y][room_x].char)
                            else:
                                self.tile_window.addch(i, j, game_room.tiles[room_y][room_x].char)

    def open_inventory(self):
        inventory_window = curses.newwin(self.window_height, self.window_width, 0, 1)
        self.draw_borders(inventory_window)

        inventory_window.keypad(1)
        
        items = list(self.player.items)
        items += self.player.countable_items

        display_names = []
        for item in items:
            line = f'{item.name}'
            if issubclass(type(item), Items.CountableItem):
                line += f' x{item.amount}'
            if issubclass(type(item), Items.EquipableItem):
                line += f' ({item.slot})'
            display_names += [line]

        inventory_window.addstr(1, 1, 'Inventory')
        # initial items print
        choice_id = 0
        for i in range(min(len(display_names), self.window_height - 4)):
            if i == choice_id:
                inventory_window.addstr(i + 4, 1, '> ')
            inventory_window.addstr(i + 4, 3, display_names[i])
        if len(display_names) > self.window_height - 3:
            inventory_window.addstr(self.window_height, self.mid_x + 1, 'V')
        inventory_window.refresh()

        display_length = min(len(display_names), self.window_height - 4)
        while True:
            key = inventory_window.getch()
            inventory_window.clear()

            if key == 27: # ESC
                break
            if key == 259: # UP
                choice_id -= 1
                if choice_id < 0: choice_id = len(display_names) - 1
            if key == 258: # DOWN
                choice_id += 1
                if choice_id >= len(display_names): choice_id = 0

            if len(display_names) > display_length:
                if choice_id != 0:
                    inventory_window.addstr(3, self.mid_x + 1, '^')
                if choice_id + display_length > len(display_names):
                    start = len(display_names) - display_length
                else: 
                    start = choice_id
                end = start + display_length
            else:
                start = 0
                end = display_length
            
            inventory_window.addstr(1, 1, 'Inventory')

            if choice_id + display_length < len(display_names):
                inventory_window.addstr(4, 1, '> ')
                if len(display_names) > display_length:
                    inventory_window.addstr(self.window_height, self.mid_x + 1, 'V')

            for i in range(start, end):
                if i == choice_id:
                    if len(display_names) > display_length:
                        if choice_id + display_length >= len(display_names):
                            inventory_window.addstr(i + 4 - start, 1, '> ')
                    else:
                        inventory_window.addstr(i + 4 - start, 1, '> ')
                inventory_window.addstr(i + 4 - start, 3, display_names[i])
            
            self.draw_borders(inventory_window)
            inventory_window.refresh()
        # end of method
        inventory_window.clear()
        inventory_window.refresh()

    def interact_with_chest(self, chest_tile):
        message = ' '.join([item.name for item in chest_tile.items])
        self.message_box(message, ['ok'])

    def get_interactable_tiles(self, game_room, y, x):
        y_lim = game_room.height
        x_lim = game_room.width
        result = []
        # North
        if not y < 0 and game_room.tiles[y - 1][x].interactable:
            result += [[game_room.tiles[y - 1][x], [56, 259]]]
        # South
        if not y >= y_lim and game_room.tiles[y + 1][x].interactable:
            result += [[game_room.tiles[y + 1][x], [50, 258]]]
        # West
        if not x < 0 and game_room.tiles[y][x - 1].interactable:
            result += [[game_room.tiles[y][x - 1], [52, 260]]]
        # East
        if not x >= x_lim and game_room.tiles[y][x + 1].interactable:
            result += [[game_room.tiles[y][x + 1], [54, 261]]]
        # NE
        if not (y < 0 and not self.x >= x_lim) and game_room.tiles[y - 1][x + 1].interactable:
            result += [[game_room.tiles[y - 1][x + 1], [117, 57]]]
        # NW
        if not (y < 0 and x < 0) and game_room.tiles[y - 1][x - 1].interactable:
            result += [[game_room.tiles[y - 1][x - 1], [121, 55]]]
        # SW
        if not (y >= y_lim and x < 0) and game_room.tiles[y + 1][x - 1].interactable:
            result += [[game_room.tiles[y + 1][x - 1], [98, 49]]]
        # SE
        if not (y >= y_lim and x >= x_lim) and game_room.tiles[y + 1][x + 1].interactable:
            result += [[game_room.tiles[y + 1][x + 1], [110, 51]]]
        return result

    def set_env_var(self, var, value):
        self.env_vars[var] = value

    def get_env_var(self, var):
        if not var in self.env_vars.keys():
            return None
        var = self.env_vars[var]
        return var

    def exec_line(self, line, scripts):
        words = line.split()
        command = words[0]
        if command == 'run':
            script_name = words[1]
            return self.exec_script(script_name, scripts)
        if command == 'set':
            var = words[1]
            value = ' '.join(words[2:])
            real_value = self.get_true_value(value)
            if real_value == None:
                raise Exception(f'ERR: value {value} not recognized')
            if var == 'player.health':
                self.player.health = min(real_value, self.player.max_health)                        
                return False
            if var == 'player.mana':
                self.player.mana = min(real_value, self.player.max_mana)                        
                return False
            self.set_env_var(var, real_value)
            return False
        if command == 'unset':
            var = words[1]
            if not var in self.env_vars:
                raise Exception(f'ERR: var {var} not recognized')
            self.env_vars.pop(var, None)
            return False
        if command == 'add':
            var = words[1]
            value = ' '.join(words[2:])
            real_value = self.get_true_value(value)
            if var == 'player.health':
                self.player.add_health(real_value)
                return False
            if var == 'player.mana':
                self.player.add_mana(real_value)
                return False
            if var in self.env_vars:
                if isinstance(self.get_env_var(var), str):
                    self.set_env_var(var, self.get_env_var(var) + str(real_value))
                else:
                    self.set_env_var(var, self.get_env_var(var) + real_value)
                return False
            raise Exception(f'ERR: variable {var} is not in env_vars')
        if command == 'sub':
            var = words[1]
            value = words[2]
            if not value.isdigit():
                raise Exception(f'ERR: {value} is not a digit')
            real_value = int(value)
            if var == 'player.health':
                self.player.add_health(-real_value)
                return False
            if var == 'player.mana':
                self.player.add_mana(-real_value)
                return False
            if var in self.env_vars:
                self.set_env_var(var, self.get_env_var(var) - real_value)
                return False
            raise Exception(f'ERR: variable {var} is not in env_vars')
        if command == 'mb':
            choices = words[1].split('_')
            var = ' '.join(words[2:])
            real_var = self.get_true_value(var)
            if real_var == None:
                raise Exception(f'ERR: {var} not recognized')  
            answer = self.message_box(str(real_var), choices, width=self.window_width - 4, ypos=2, xpos=2)
            self.set_env_var('_mb_result', answer)
            return False
        if command == 'say':
            replies = words[1].split('_')
            var = ' '.join(words[2:])
            real_var = self.get_true_value(var)
            if real_var == None:
                raise Exception(f'ERR: {var} not recognized')
            reply = self.display_dialog(str(real_var), replies)
            self.set_env_var('_reply', reply)
            return False
        if command == 'move':
            entity_name = words[1]
            move_y = int(words[2])
            move_x = int(words[3])
            if entity_name == 'player':
                self.player_y += move_y
                self.player_x += move_x
                return False
        if command == 'if':
            words.pop(0)
            reverse = False
            do_if = False
            if words[0] == 'not':
                reverse = True
                words.pop(0)
            if words[0] == 'set':
                var = words[1]
                do_if = var in self.env_vars.keys()
            if words[1] == '==':
                var1 = words[0]
                var2 = ' '.join(words[2:words.index('then')])
                real_var1 = self.get_true_value(var1)
                real_var2 = self.get_true_value(var2)
                do_if = real_var1 == real_var2
            if reverse != do_if:
                return self.exec_line(' '.join(words[words.index('then') + 1:]), scripts)
            return False
        if command == 'stop':
            return True
        if command == 'return':
            var = ' '.join(words[1:])
            real_var = self.get_true_value(var)
            self.set_env_var('return_value', real_var)
            return False
        raise Exception(f'ERR: command {words[0]} not recognized')

    def get_true_value(self, s):
        if s.lstrip('-').isdigit():
            return int(s)
        if s[0] == '"' and s[len(s) - 1] == '"':
            return s[1:len(s) - 1]
        if s.lower() == 'true':
            return True
        if s.lower() == 'false':
            return False
        if s == 'player.health':
            return self.player.health
        if s == 'player.mana':
            return self.player.mana
        if s == 'player.name':
            return self.player.name
        if s == 'player.y':
            return self.player_y
        if s == 'player.x':
            return self.player_x
        if s in self.env_vars:
            return self.get_env_var(s)
        return None

    def exec_script(self, name, scripts):
        script = scripts[name]
        # if self.debug: self.message_box(script[0], ['Ok'], width=self.window_width - 3, ypos=2, xpos=2, additional_lines=script[1:])
        for script_line in script:
            if script_line == '':
                continue
            quit = self.exec_line(script_line, scripts)
            if quit:
                return True
            
    def get_terminal_command(self):
        self.addstr(self.window_height, 1, '> ')
        self.stdscr.refresh()
        w = curses.newwin(1, self.WIDTH - 3, self.window_height, 3)
        curses.curs_set(1)
        w.keypad(1)
        box = textpad.Textbox(w)
        box.edit(self._terminal_command_validator)
        result = box.gather()
        curses.curs_set(0)
        w.clear()
        w.refresh()
        self.addstr(self.window_height, 1, '  ')
        self.stdscr.refresh()
        return result

    def _terminal_command_validator(self, ch):
        if ch in [127, 8]:
            return 8
        return ch