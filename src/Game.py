import curses
import curses.textpad as textpad
import json

import os
import gamelib.SaveFile as SaveFile

from ui.Menu import Menu
from ui.Buttons import Button, ActionButton

from gamelib.Entities import Player

import Utility
import gamelib.Map as Map
import gamelib.Items as Items

class Game:
    def __init__(self, saves_path, assets_path):
        self.debug = False
        self.assets_path = assets_path
        self.saves_path = saves_path
        self.max_name_len = 20
        self.starting_map = 'map1'


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

        new_game_button = ActionButton('new_game_button', 'New game', self.main_menu, self.new_game_action)

        load_button = ActionButton('load_button', 'Load', self.main_menu, self.load_game_action)

        main_to_settings_button = Button('settings_button', 'Settings', self.main_menu)
        main_to_settings_button.connect_to(settings_menu)

        main_to_credits_button = Button('credits_button', 'Credits', self.main_menu)
        main_to_credits_button.connect_to(credits_menu)

        exit_button = ActionButton('exit_button', 'Exit', self.main_menu, self.exit_action)

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
            if self.debug: win.addstr(0, 0, f'KEY: |{key}|\t{height}; {width}')
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
        SaveFile.save(player, self.starting_map, self.saves_path)
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
            button = ActionButton(f'load_{ch_names[i]}_button', save_desc[i], self.load_menu, self.load_character_pick_action)
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
        try:
            data = SaveFile.load(character_name, self.saves_path)
            if data == -1:
                raise Exception(f'ERR: save file of character with name {character_name} not found in {self.saves_path}')
            self.player = Player.from_json(data['player'])
            game_map = Map.Map.by_name(data['map_name'], f'{self.assets_path}/maps/', self.assets_path)
            self.player_y, self.player_x = game_map.player_spawn_y, game_map.player_spawn_x
            if 'player_y' in data:
                self.player_y = data['player_y']
            if 'player_x' in data:
                self.player_x = data['player_x']
        except Exception as ex:
            if self.debug: raise ex
            if self.message_box(f'Character {character_name} seems to be corrupt, delete file?', ['No', 'Yes']) == 'Yes':
                SaveFile.delete_save_file(character_name, self.saves_path)
                self.load_menu.remove_button_with_name(f'load_{character_name}_button')
            return
            
        self.stdscr.clear()

        # set some values
        self.window_height = self.HEIGHT * 2 // 3
        if self.window_height % 2 == 0: self.window_height -= 1
        self.window_width = self.WIDTH - self.max_name_len - 8

        self.window_height -= 1
        self.window_width -= 1

        # permanent display
        self.tile_window = curses.newwin(self.window_height, self.window_width, 1, 1)
        self.tile_window.keypad(1)
        self.display_info_ui()
        self.display_player_info()
        self.stdscr.refresh()

        visible_range = 10
        mid_y = self.window_height // 2 
        mid_x = self.window_width // 2

        self.tile_window.addstr(mid_y, mid_x, '@')

        self.draw_tiles(mid_y, mid_x, visible_range, game_map)
        self.tile_window.addstr(mid_y, mid_x, '@')

        # main game loop
        while True:
            key = self.tile_window.getch()
            self.tile_window.clear()
            if key == 81 and self.message_box('Are you sure you want to quit? (Progress will be saved)', ['No', 'Yes'],width=self.window_width - 3, ypos=2, xpos=2) == 'Yes':
                SaveFile.save(self.player, game_map.name, self.saves_path, player_y=self.player_y, player_x=self.player_x)
                break
            if self.debug and key == 32:
                self.player.add_health(1)
                self.player.add_mana(1)
            if self.debug and key == 10:
                self.player.add_health(-1)
                self.player.add_mana(-1)

            # movement management
            y_lim = game_map.height
            x_lim = game_map.width
            # North
            if key in [56, 259] and not self.player_y < 0 and not game_map.tiles[self.player_y - 1][self.player_x].solid:
                self.player_y -= 1
            # South
            if key in [50, 258] and not self.player_y >= y_lim and not game_map.tiles[self.player_y + 1][self.player_x].solid:
                self.player_y += 1
            # West
            if key in [52, 260] and not self.player_x < 0 and not game_map.tiles[self.player_y][self.player_x - 1].solid:
                self.player_x -= 1
            # East
            if key in [54, 261] and not self.player_x >= x_lim and not game_map.tiles[self.player_y][self.player_x + 1].solid:
                self.player_x += 1
            # NE
            if key in [117, 57] and not (self.player_y < 0 and not self.player_x >= x_lim) and not game_map.tiles[self.player_y - 1][self.player_x + 1].solid:
                self.player_y -= 1
                self.player_x += 1
            # NW
            if key in [121, 55] and not (self.player_y < 0 and self.player_x < 0) and not game_map.tiles[self.player_y - 1][self.player_x - 1].solid:
                self.player_y -= 1
                self.player_x -= 1
            # SW
            if key in [98, 49] and not (self.player_y >= y_lim and self.player_x < 0) and not game_map.tiles[self.player_y + 1][self.player_x - 1].solid:
                self.player_y += 1
                self.player_x -= 1
            # SE
            if key in [110, 51] and not (self.player_y >= y_lim and self.player_x >= x_lim) and not game_map.tiles[self.player_y + 1][self.player_x + 1].solid:
                self.player_y += 1
                self.player_x += 1
            # open inventory
            if key == 105: # i
                self.open_inventory()
                
            tile = game_map.tiles[self.player_y][self.player_x]
            # check if is standing on a door
            if isinstance(tile, Map.DoorTile) and self.message_box(f'Use door?', ['No', 'Yes'], width=self.window_width - 3, ypos=2, xpos=2) == 'Yes':
                destination_map = tile.to
                game_map = Map.Map.by_name(destination_map, f'{self.assets_path}/maps/', self.assets_path, player_spawn_char=tile.char)
                self.player_y, self.player_x = game_map.player_spawn_y, game_map.player_spawn_x

            self.draw_tiles(mid_y, mid_x, visible_range, game_map)
            # last to display
            self.tile_window.addstr(mid_y, mid_x, '@')

            self.display_player_info()
            self.tile_window.refresh()
            self.stdscr.refresh()

        # end of method
        self.tile_window.clear()
        self.tile_window.refresh()
        # del self.tile_window
        self.stdscr.clear()
        self.stdscr.refresh()
        self.current_menu = self.main_menu

    def display_info_ui(self):
        s = '1234567891234567891234'
        textpad.rectangle(self.stdscr, 0, 0, self.window_height + 2, self.window_width + 1)
        self.addstr(1, self.window_width + 3, f'Name: {self.player.name}')
        self.addstr(2, self.window_width + 3, f'Class: {self.player.class_name}')
        self.addstr(4, self.window_width + 3, f'Health:          (   /   )') # left: 19
        self.addstr(5, self.window_width + 3, f'Mana:            (   /   )') # left: 21
        self.addstr(7, self.window_width + 3, f'STR:') # left: 22
        self.addstr(8, self.window_width + 3, f'DEX:') # left: 22
        self.addstr(9, self.window_width + 3, f'INT:') # left: 22
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
        
    def draw_tiles(self, mid_y, mid_x, visible_range, game_map):
        for i in range(max(0, mid_y - visible_range), min(self.window_height, mid_y + visible_range + 1)):
            for j in range(max (0, mid_x - visible_range), min(self.window_width, mid_x + visible_range + 1)):
                if Utility.distance(i, j, mid_y, mid_x) < visible_range:
                    if i == self.window_height - 1 and j == self.window_width - 1:
                        break
                    map_y = i + self.player_y - mid_y
                    map_x = j + self.player_x - mid_x
                    if map_y < 0 or map_x < 0 or map_y >= game_map.height or map_x >= game_map.width:
                        self.tile_window.addch(i, j, '#')
                    else:
                        self.tile_window.addch(i, j, game_map.tiles[map_y][map_x].char)
                        
    def open_inventory(self):
        inventory_window = curses.newwin(self.window_height, self.window_width, 1, 1)
        inventory_window.keypad(1)

        mid_x = self.window_width // 2
        
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

        inventory_window.addstr(0, 0, 'Inventory')
        # initial items print
        choice_id = 0
        for i in range(min(len(display_names), self.window_height - 4)):
            if i == choice_id:
                inventory_window.addstr(i + 3, 0, '> ')
            inventory_window.addstr(i + 3, 2, display_names[i])
        if len(display_names) > self.window_height - 3:
            inventory_window.addstr(self.window_height - 1, mid_x, 'V')
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
                    inventory_window.addstr(2, mid_x, '^')
                if choice_id + display_length > len(display_names):
                    start = len(display_names) - display_length
                else: 
                    start = choice_id
                end = start + display_length
            else:
                start = 0
                end = display_length
            
            inventory_window.addstr(0, 0, 'Inventory')

            if choice_id + display_length < len(display_names):
                inventory_window.addstr(3, 0, '> ')
                if len(display_names) > display_length:
                    inventory_window.addstr(self.window_height - 1, mid_x, 'V')

            for i in range(start, end):
                if i == choice_id:
                    if len(display_names) > display_length:
                        if choice_id + display_length >= len(display_names):
                            inventory_window.addstr(i + 3 - start, 0, '> ')
                    else:
                        inventory_window.addstr(i + 3 - start, 0, '> ')
                inventory_window.addstr(i + 3 - start, 2, display_names[i])

            
            inventory_window.refresh()

            inventory_window.refresh()
        # end of method
        inventory_window.clear()
        inventory_window.refresh()