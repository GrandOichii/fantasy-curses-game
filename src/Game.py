import curses
import curses.textpad as textpad
import json
from math import sqrt
import os
from gamelib.Spells import BloodSpell, NormalSpell

from ui.Menu import Menu
from ui.Buttons import Button, ActionButton

import Utility
import gamelib.Room as Room
import gamelib.Items as Items
import gamelib.Map as Map
import gamelib.SaveFile as SaveFile

from gamelib.Entities import Player
from gamelib.Combat import CombatEncounter

class Game:
    def __init__(self, saves_path, assets_path, rooms_path, map_path, starting_room='index'):
        self.debug = False
        self.assets_path = assets_path
        self.saves_path = saves_path
        self.rooms_path = rooms_path
        self.map_path = map_path
        self.max_name_len = 20
        self.starting_room = starting_room
        self.game_speed = 200


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

    def main(self, stdscr):
        if self.debug: self.draw_borders(stdscr)
        self.stdscr = stdscr
        self.HEIGHT, self.WIDTH = self.stdscr.getmaxyx()
        self.menu_choice_id = 0

        # remove cursor
        curses.curs_set(0)
        curses.mousemask(1)

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
        self.player = Player.from_json(data['player'], self.assets_path)
        self.env_vars = data['env_vars']
        self.game_room = Room.Room.by_name(data['room_name'], self.rooms_path, self.assets_path, self.env_vars)

        self.player_y, self.player_x = self.game_room.player_spawn_y, self.game_room.player_spawn_x
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

        self.camera_dy = 0
        self.camera_dx = 0

        # permanent display
        self.tile_window = curses.newwin(self.window_height, self.window_width, 0, 1)
        self.draw_borders(self.tile_window)
        # self.tile_window.nodelay(True)
        # self.tile_window.timeout(self.game_speed)

        self.tile_window.keypad(1)
        self.draw_info_ui()
        self.draw_player_info()
        self.stdscr.refresh()

        self.MINI_MAP_HEIGHT = 7
        self.MINI_MAP_WIDTH = 7
        self.mini_map_window = curses.newwin(self.MINI_MAP_HEIGHT + 2, self.MINI_MAP_WIDTH + 2, 13, self.window_width + 4)
        self.draw_borders(self.mini_map_window)
        self.mini_map_window.refresh()
        self.full_map = None
        if os.path.exists(self.map_path):
            self.full_map = Map.Map(self.map_path)

        self.mid_y = self.window_height // 2 
        self.mid_x = self.window_width // 2

        self.draw_tile_window()

        if '_load' in self.game_room.scripts:
            self.exec_script('_load', self.game_room.scripts)

        if self.full_map != None:
            self.draw_mini_map(self.game_room.name)

        self.tile_window.refresh()
        if self.game_room.display_name != '':
            self.draw_room_display_name(self.game_room.display_name)

        # main game loop
        self.main_game_loop()
        
        # end of method
        self.tile_window.clear()
        self.tile_window.refresh()
        self.stdscr.clear()
        self.stdscr.refresh()
        self.current_menu = self.main_menu

    def main_game_loop(self):
        entered_room = False
        encounter_ready, encounter_enemy_code = self.check_for_encounters()
        self.game_running = True

        while self.game_running:
            if '_tick' in self.game_room.scripts:
                self.exec_script('_tick', self.game_room.scripts)
            key = self.tile_window.getch()
            self.tile_window.clear()
            if key == 81 and self.message_box('Are you sure you want to quit? (Progress will be saved)', ['No', 'Yes'],width=self.window_width - 4, ypos=2, xpos=2) == 'Yes':
                self.save_enemy_env_vars()
                SaveFile.save(self.player, self.game_room.name, self.saves_path, player_y=self.player_y, player_x=self.player_x, env_vars=self.env_vars)
                break
            # if self.debug and key == 126:
            if key == 126:
                command = self.get_terminal_command()
                self.exec_line(command, self.game_room.scripts)

            # movement management
            y_lim = self.game_room.height
            x_lim = self.game_room.width
            # North
            if key in [56, 259] and not self.player_y < 0 and not self.game_room.tiles[self.player_y - 1][self.player_x].solid:
                self.player_y -= 1
                entered_room = True
            # South
            if key in [50, 258] and not self.player_y >= y_lim and not self.game_room.tiles[self.player_y + 1][self.player_x].solid:
                self.player_y += 1
                entered_room = True
            # West
            if key in [52, 260] and not self.player_x < 0 and not self.game_room.tiles[self.player_y][self.player_x - 1].solid:
                self.player_x -= 1
                entered_room = True
            # East
            if key in [54, 261] and not self.player_x >= x_lim and not self.game_room.tiles[self.player_y][self.player_x + 1].solid:
                self.player_x += 1
                entered_room = True
            # NE
            if key in [117, 57] and not (self.player_y < 0 and not self.player_x >= x_lim) and not self.game_room.tiles[self.player_y - 1][self.player_x + 1].solid:
                self.player_y -= 1
                self.player_x += 1
                entered_room = True
            # NW
            if key in [121, 55] and not (self.player_y < 0 and self.player_x < 0) and not self.game_room.tiles[self.player_y - 1][self.player_x - 1].solid:
                self.player_y -= 1
                self.player_x -= 1
                entered_room = True
            # SW
            if key in [98, 49] and not (self.player_y >= y_lim and self.player_x < 0) and not self.game_room.tiles[self.player_y + 1][self.player_x - 1].solid:
                self.player_y += 1
                self.player_x -= 1
                entered_room = True
            # SE
            if key in [110, 51] and not (self.player_y >= y_lim and self.player_x >= x_lim) and not self.game_room.tiles[self.player_y + 1][self.player_x + 1].solid:
                self.player_y += 1
                self.player_x += 1
                entered_room = True
            # interact
            if key == 101: # e
                interactable_tiles = self.get_interactable_tiles(self.player_y, self.player_x)
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
                            self.exec_script(i_tile.script_name, self.game_room.scripts)
                        if isinstance(i_tile, Room.HiddenTile) and isinstance(i_tile.actual_tile, Room.ScriptTile):
                            self.exec_script(i_tile.actual_tile.script_name, self.game_room.scripts)
                    else:
                        # add to log history
                        a=1
            # open inventory
            if key == 105: # i
                self.draw_inventory()
            # initiate combat
            if key == 99: # c
                if encounter_ready:
                    self.initiate_encounter_with(encounter_enemy_code)
                else:
                    self.message_box('You are not within range to attack anybody!', ['Ok'], width=self.window_width - 4, ypos=2, xpos=2)
            if self.game_running:
                tile = self.game_room.tiles[self.player_y][self.player_x]
                if isinstance(tile, Room.DoorTile) and entered_room:
                    entered_room = False
                    destination_room = tile.to
                    door_code = tile.door_code
                    self.set_env_var('_last_door_code', door_code)
                    self.game_room = Room.Room.by_name(destination_room, self.rooms_path, self.assets_path, door_code=door_code, env_vars=self.env_vars)
                    self.player_y, self.player_x = self.game_room.player_spawn_y, self.game_room.player_spawn_x
                    self.tile_window.clear()
                    self.tile_window.refresh()
                    if '_load' in self.game_room.scripts:
                        self.exec_script('_load', self.game_room.scripts)
                    if '_enter' in self.game_room.scripts:
                        self.exec_script('_enter', self.game_room.scripts)
                if isinstance(tile, Room.PressurePlateTile):
                    self.exec_script(tile.script_name, self.game_room.scripts)
                if isinstance(tile, Room.HiddenTile) and self.get_env_var(tile.signal) == True and isinstance(tile.actual_tile, Room.PressurePlateTile):
                    self.exec_script(tile.actual_tile.script_name, self.game_room.scripts)       

                self.update_entities()

                # check if encounters are available

                self.draw_tile_window()
                self.draw_player_info()
                self.tile_window.refresh()
                self.stdscr.refresh()
                if self.game_room.display_name != '':
                    self.draw_room_display_name(self.game_room.display_name)

                encounter_ready, encounter_enemy_code = self.check_for_encounters()
                
                if key == 120: # x
                    self.tile_description_mode()      

    def check_for_encounters(self):
        encounter_ready = False
        enemy_code = None
        min_d = -1
        min_enemy_code = None
        for enemy_code in self.game_room.enemies_data:
            enemy = self.game_room.enemies_data[enemy_code]
            if enemy.health > 0:
                d = Utility.distance(enemy.y, enemy.x, self.player_y, self.player_x)
                if d <= self.player.get_range(self.game_room.visible_range):
                    if min_d == -1 or d < min_d:
                        min_d = d
                        min_enemy_code = enemy_code
        if min_enemy_code != None:
            enemy = self.game_room.enemies_data[min_enemy_code]
            encounter_ready = True
            s = f'[ Press [c] to initiate combat with {enemy.name} ]'
            y = self.window_height - 2
            x = self.window_width // 2 - len(s) // 2
            self.tile_window.addstr(y, x, s)
        return (encounter_ready, enemy_code)                 

    def update_entities(self):
        self.player.regenerate_mana()
        for enemy_code in self.game_room.enemies_data:
            enemy = self.game_room.enemies_data[enemy_code]
            enemy.regenerate_mana()

    def save_enemy_env_vars(self):
        for enemy_code in self.game_room.enemies_data:
            enemy = self.game_room.enemies_data[enemy_code]
            f = f'enemies_{self.game_room.name}_{enemy_code}_'
            self.set_env_var(f'{f}health', enemy.health)
            self.set_env_var(f'{f}mana', enemy.mana)
            self.set_env_var(f'{f}y', enemy.y)
            self.set_env_var(f'{f}x', enemy.x)

    def tile_description_mode(self):
        cursor_y = self.mid_y
        cursor_x = self.mid_x

        cursor_map_y = self.player_y
        cursor_map_x = self.player_x

        # initial display
        self.tile_window.addch(cursor_y, cursor_x, '@', curses.A_REVERSE)
        self.tile_window.addstr(1, 1, f'[{self.player.name}]')

        while True:
            key = self.tile_window.getch()
            if key == 27: # ESC
                break
            if key == 120: # x
                break
            self.tile_window.clear()
            # North
            if key in [56, 259] and cursor_map_y != 0 and Utility.distance(cursor_map_y - 1, cursor_map_x, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_y -= 1
                cursor_map_y -= 1
            # South
            if key in [50, 258] and cursor_map_y != self.game_room.height - 1 and Utility.distance(cursor_map_y + 1, cursor_map_x, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_y += 1
                cursor_map_y += 1
            # West
            if key in [52, 260] and cursor_map_x != 0 and Utility.distance(cursor_map_y, cursor_map_x - 1, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_x -= 1
                cursor_map_x -= 1
            # East
            if key in [54, 261] and cursor_map_x != self.game_room.width - 1 and Utility.distance(cursor_map_y, cursor_map_x + 1, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_x += 1
                cursor_map_x += 1
            
            self.draw_tiles(self.player_y, self.player_x, self.game_room.visible_range)
            self.tile_window.addstr(self.mid_y, self.mid_x, '@')
            display_name = ''
            if cursor_y == self.mid_y and cursor_x == self.mid_x:
                self.tile_window.addch(cursor_y, cursor_x, '@', curses.A_REVERSE)
                display_name = self.player.name
            else:
                tile = self.game_room.tiles[cursor_map_y][cursor_map_x]
                name = tile.name
                char = tile.char
                if name == 'hidden tile':
                    name = tile.actual_tile.name
                    char = tile.actual_tile.char
                    if self.get_env_var(tile.signal) != True:
                        name = 'wall'
                        char = '#'
                if tile.char == ' ':
                    name = 'floor'
                display_name = name
                self.tile_window.addch(cursor_y, cursor_x, char, curses.A_REVERSE)
            for enemy in list(self.game_room.enemies_data.values()):
                y = enemy.y + self.mid_y - self.player_y
                x = enemy.x + self.mid_x - self.player_x
                if Utility.distance(self.player_y, self.player_x, enemy.y, enemy.x) < self.game_room.visible_range:
                    if y == cursor_y and x == cursor_x:
                        self.tile_window.addch(y, x, enemy.char, curses.A_REVERSE)
                        display_name = enemy.name
                    else:
                        self.tile_window.addch(y, x, enemy.char)
            if len(display_name) != 0:
                self.tile_window.addstr(1, 1, f'[{display_name}]')
            self.draw_borders(self.tile_window)
        # clean-up
        self.tile_window.clear()
        self.draw_tile_window()

    def interact_with_chest(self, chest_tile):
        max_win_height = 9

        items = self.game_room.chest_contents[chest_tile.chest_code]

        item_names = []
        codes = []
        for item in items:
            if self.get_env_var(items[item]) != True:
                if isinstance(item, Items.GoldPouch):
                    item_names += [f'{item.amount} gold']
                elif isinstance(item, Items.CountableItem):
                    item_names += [f'{item.name} x{item.amount}']
                else:
                    item_names += [item.name]
                codes += [items[item]]

        if len(item_names) == 0:
            self.message_box('Chest is empty.', ['Ok'])
            return
        win_height = min(max_win_height, len(item_names) * 2 + 1)
        win_width = max([len(ls) for ls in item_names]) + 2
        chest_window = curses.newwin(win_height, win_width, self.mid_y, self.mid_x + 3)
        chest_window.keypad(1)

        choice_id = 0
        cursor = 0
        displayed_item_count = win_height // 2

        self.draw_borders(chest_window)
        # initial display
        # lines
        for i in range(1, displayed_item_count):
            chest_window.addch(2 * i, 0, curses.ACS_LTEE)
            chest_window.addch(2 * i, win_width - 1, curses.ACS_RTEE)
            for j in range(1, win_width - 1):
                chest_window.addch(2 * i, j, curses.ACS_HLINE)
        # initial item display
        for i in range(displayed_item_count):
            if i == cursor:
                chest_window.addstr(1 + 2 * i, 1, item_names[i], curses.A_REVERSE)
            else:
                chest_window.addstr(1 + 2 * i, 1, item_names[i])
        if len(item_names) > displayed_item_count:
            chest_window.addch(win_height - 2, win_width - 1, curses.ACS_DARROW)

        taken_codes = []
        page_n = 0
        while True:
            # if self.debug: chest_window.addstr(0, 0, f'pn: {page_n} cid: {choice_id}')
            # if self.debug: chest_window.addstr(win_height - 1, 0, f'curs: {cursor}')
            key = chest_window.getch()
            # input processing
            if key == 27: # ESC
                break
            if key == 259: # UP
                choice_id -= 1
                cursor -= 1
                if cursor < 0:
                    if len(item_names) > displayed_item_count:
                        if page_n == 0:
                            cursor = displayed_item_count - 1
                            choice_id = len(item_names) - 1
                            page_n = len(item_names) - displayed_item_count
                        else:
                            page_n -= 1
                            cursor += 1
                    else:
                        cursor = len(item_names) - 1
                        choice_id = cursor
            if key == 258: # DOWN
                choice_id += 1
                cursor += 1
                if len(item_names) > displayed_item_count:
                    if cursor >= displayed_item_count:
                        cursor -= 1
                        page_n += 1
                        if choice_id == len(item_names):
                            choice_id = 0
                            cursor = 0
                            page_n = 0
                else:
                    if cursor >= len(item_names):
                        cursor = 0
                        choice_id = 0
            if key == 10: # ENTER
                if choice_id == -1:
                    break
                item_code = codes[choice_id]
                taken_codes += [item_code]
                item_names.pop(choice_id)
                codes.pop(choice_id)
                if len(item_names) > displayed_item_count:
                    if page_n == len(item_names) - displayed_item_count + 1:
                        page_n -= 1
                        choice_id -= 1
                else:
                    if page_n == 1:
                        page_n = 0
                        # cursor += 1
                        choice_id -= 1
                    if choice_id == len(item_names):
                        cursor -= 1
                        choice_id -= 1
                    pass
                
            for i in range(displayed_item_count):
                chest_window.addstr(1 + 2 * i, 1, ' ' * (win_width - 2))
            # clear the arrows
            chest_window.addch(1, win_width - 1, curses.ACS_VLINE)
            chest_window.addch(win_height - 2, win_width - 1, curses.ACS_VLINE)
            # displaying the items
            if len(item_names) > displayed_item_count:
                if page_n != 0:
                    chest_window.addch(1, win_width - 1, curses.ACS_UARROW)
                if page_n != len(item_names) - displayed_item_count:
                    chest_window.addch(win_height - 2, win_width - 1, curses.ACS_DARROW)
            for i in range(min(len(item_names), displayed_item_count)):
                if i == cursor:
                    chest_window.addstr(1 + 2 * i, 1, item_names[i + page_n], curses.A_REVERSE)
                else:
                    chest_window.addstr(1 + 2 * i, 1, item_names[i + page_n])
        # clear off taken items
        for code in taken_codes:
            self.set_env_var(code, True)
        # add taken items to inventory
        for code in taken_codes:
            for item in items:
                if items[item] == code:
                    self.player.add_item(item)

    def get_interactable_tiles(self, y, x):
        y_lim = self.game_room.height
        x_lim = self.game_room.width
        result = []
        # North
        if not y < 0 and self.game_room.tiles[y - 1][x].interactable:
            result += [[self.game_room.tiles[y - 1][x], [56, 259]]]
        # South
        if not y >= y_lim and self.game_room.tiles[y + 1][x].interactable:
            result += [[self.game_room.tiles[y + 1][x], [50, 258]]]
        # West
        if not x < 0 and self.game_room.tiles[y][x - 1].interactable:
            result += [[self.game_room.tiles[y][x - 1], [52, 260]]]
        # East
        if not x >= x_lim and self.game_room.tiles[y][x + 1].interactable:
            result += [[self.game_room.tiles[y][x + 1], [54, 261]]]
        # NE
        if not (y < 0 and not self.x >= x_lim) and self.game_room.tiles[y - 1][x + 1].interactable:
            result += [[self.game_room.tiles[y - 1][x + 1], [117, 57]]]
        # NW
        if not (y < 0 and x < 0) and self.game_room.tiles[y - 1][x - 1].interactable:
            result += [[self.game_room.tiles[y - 1][x - 1], [121, 55]]]
        # SW
        if not (y >= y_lim and x < 0) and self.game_room.tiles[y + 1][x - 1].interactable:
            result += [[self.game_room.tiles[y + 1][x - 1], [98, 49]]]
        # SE
        if not (y >= y_lim and x >= x_lim) and self.game_room.tiles[y + 1][x + 1].interactable:
            result += [[self.game_room.tiles[y + 1][x + 1], [110, 51]]]
        return result

    # drawing

    def draw_borders(self, w):
        w.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def draw_info_ui(self):
        s = '1234567891234567891234'
        self.addstr(0, self.window_width + 2, f'Name: {self.player.name}')
        self.addstr(1, self.window_width + 2, f'Class: {self.player.class_name}')
        self.addstr(2, self.window_width + 2, f'Gold: ')
        self.addstr(4, self.window_width + 2, f'Health:          (   /   )') # left: 19
        self.addstr(5, self.window_width + 2, f'  Mana:          (   /   )') # left: 21
        self.addstr(7, self.window_width + 2, f'STR:') # left: 22
        self.addstr(8, self.window_width + 2, f'DEX:') # left: 22
        self.addstr(9, self.window_width + 2, f'INT:') # left: 22
        self.addstr(11, self.window_width + 2, 'Prompt: ')
        self.stdscr.refresh()

    def draw_player_info(self):
        self.addstr(2, self.window_width + 2 + 6, ' ' * (self.WIDTH - self.window_width - 2 - 6))
        self.addstr(2, self.window_width + 2 + 6, f'{self.player.gold}')

        health_info = ' ' * (3 - len(str(self.player.health))) + f'{self.player.health}'
        self.addstr(4, self.window_width + 20, f'{health_info}')
        max_health_info =  ' ' * (3 - len(str(self.player.max_health))) + f'{self.player.max_health}'
        self.addstr(4, self.window_width + 24, f'{max_health_info}')
        self.addstr(4, self.window_width + 9, Utility.calc_pretty_bars(self.player.health, self.player.max_health, 10))
        
        mana_info =  ' ' * (3 - len(str(self.player.mana))) + f'{self.player.mana}'
        self.addstr(5, self.window_width + 20, f'{mana_info}')
        max_mana_info =  ' ' * (3 - len(str(self.player.max_mana))) + f'{self.player.max_mana}'
        self.addstr(5, self.window_width + 24, f'{max_mana_info}')
        self.addstr(5, self.window_width + 9, Utility.calc_pretty_bars(self.player.mana, self.player.max_mana, 10))

        str_info = ' ' * (3 - len(str(self.player.STR))) + f'{self.player.STR}'
        self.addstr(7, self.window_width + 6, f'{str_info}')
        dex_info = ' ' * (3 - len(str(self.player.DEX))) + f'{self.player.DEX}'
        self.addstr(8, self.window_width + 6, f'{dex_info}')
        int_info = ' ' * (3 - len(str(self.player.INT))) + f'{self.player.INT}'
        self.addstr(9, self.window_width + 6, f'{int_info}')

    def draw_enemies(self):
        for enemy in list(self.game_room.enemies_data.values()):
            if enemy.health > 0 and sqrt((self.player_y - enemy.y) * (self.player_y - enemy.y) + (self.player_x - enemy.x) * (self.player_x - enemy.x)) < self.game_room.visible_range:
                y = enemy.y + self.mid_y - self.player_y
                x = enemy.x + self.mid_x - self.player_x
                self.tile_window.addch(y, x, enemy.char)

    def draw_torches(self):
        for i in range(self.game_room.height):
            for j in range(self.game_room.width):
                if isinstance(self.game_room.tiles[i][j], Room.TorchTile):
                    self.draw_tiles(i, j, self.game_room.tiles[i][j].visible_range)
                if isinstance(self.game_room.tiles[i][j], Room.HiddenTile) and self.get_env_var(self.game_room.tiles[i][j].signal) == True and isinstance(self.game_room.tiles[i][j].actual_tile, Room.TorchTile):
                    # !!! BIG ISSUE !!! either rework hidden tiles, or make a work-around
                    self.draw_tiles(i, j, self.game_room.tiles[i][j].actual_tile.visible_range)

    def draw_tiles(self, y, x, visible_range):
        mid_y = self.mid_y - self.player_y + y + self.camera_dy
        mid_x = self.mid_x - self.player_x + x - self.camera_dx
        for i in range(max(1, mid_y - visible_range), min(self.window_height - 1, mid_y + visible_range + 1)):
            for j in range(max (1, mid_x - visible_range), min(self.window_width - 1, mid_x + visible_range + 1)):
                if Utility.distance(i, j, mid_y, mid_x) < visible_range:
                    room_y = i + y - mid_y
                    room_x = j + x - mid_x
                    if room_y < 0 or room_x < 0 or room_y >= self.game_room.height or room_x >= self.game_room.width:
                        self.tile_window.addch(i, j, '#')
                    else:
                        if self.game_room.tiles[room_y][room_x].char == '!':
                            self.tile_window.addch(i, j, self.game_room.tiles[room_y][room_x].char, curses.A_BLINK)
                        else:
                            tile = self.game_room.tiles[room_y][room_x]
                            if isinstance(tile, Room.HiddenTile):
                                if self.get_env_var(tile.signal) == True:
                                    self.game_room.tiles[room_y][room_x].solid = self.game_room.tiles[room_y][room_x].actual_tile.solid
                                    self.game_room.tiles[room_y][room_x].interactable = self.game_room.tiles[room_y][room_x].actual_tile.interactable
                                    self.tile_window.addch(i, j, self.game_room.tiles[room_y][room_x].actual_tile.char)
                                else:
                                    self.game_room.tiles[room_y][room_x].solid = True
                                    self.game_room.tiles[room_y][room_x].interactable = False
                                    self.tile_window.addch(i, j, self.game_room.tiles[room_y][room_x].char)
                            else:
                                self.tile_window.addch(i, j, self.game_room.tiles[room_y][room_x].char)

    def draw_tile_window(self):
        self.draw_borders(self.tile_window)
        self.draw_tiles(self.player_y, self.player_x, self.game_room.visible_range)
        self.draw_torches()
        # last to display
        real_mid_y = self.mid_y + self.camera_dy
        real_mid_x = self.mid_x - self.camera_dx
        if real_mid_y > 0 and real_mid_y < self.window_height - 1 and real_mid_x > 0 and real_mid_x < self.window_width - 1:
            self.tile_window.addstr(real_mid_y, real_mid_x, '@')
        if self.full_map != None:
            self.draw_mini_map(self.game_room.name)
        self.draw_enemies()

    def draw_mini_map(self, room_name):
        hh = self.MINI_MAP_HEIGHT // 2
        hw = self.MINI_MAP_WIDTH // 2
        mini_map_tiles = self.full_map.get_mini_tiles(room_name, self.env_vars, self.MINI_MAP_HEIGHT, self.MINI_MAP_WIDTH, hh, hw)
        for i in range(self.MINI_MAP_HEIGHT):
            for j in range(self.MINI_MAP_WIDTH):
                if i == hh and j == hw:
                    self.mini_map_window.addch(1 + i, 1 + j, mini_map_tiles[i][j], curses.A_REVERSE)
                else:
                    self.mini_map_window.addch(1 + i, 1 + j, mini_map_tiles[i][j])
        self.mini_map_window.refresh()

    def draw_room_display_name(self, display_name):
        h = 3
        w = len(display_name) + 2
        y = self.window_height - 3 - 1
        x = self.window_width - w -1
        win = curses.newwin(h, w, y, x)
        win.addstr(1, 1, display_name)
        self.draw_borders(win)
        win.refresh()

    def get_display_names(self, items):
        display_names = []
        for i in range(len(items)):
            item = items[i]
            line = f'{item.name}'
            if issubclass(type(item), Items.CountableItem):
                line += f' x{item.amount}'
            if issubclass(type(item), Items.EquipableItem):
                line += f' ({item.slot})'
                for s in self.player.equipment:
                    if self.player.equipment[s] == i:
                        if item.slot == 'ARMS':
                            line += f' -> ARMS'
                        else:
                            line += f' -> {s}'
                        break
            display_names += [line]
        return display_names

    def draw_inventory(self):
        items = list(self.player.items)
        items += self.player.countable_items

        display_names = self.get_display_names(items)

        win_height = self.window_height
        win_width = self.window_width
        inventory_window = curses.newwin(win_height, win_width, 0, 1)
        inventory_window.keypad(1)
        inventory_window.addstr(1, 1, 'Inventory')
        self.draw_borders(inventory_window)

        selected_tab = 0
        tabs = ['Items', 'Equipment', 'Spells']

        inventory_window.addch(2, 0, curses.ACS_LTEE)
        inventory_window.addch(2, win_width - 1, curses.ACS_RTEE)
        for i in range(win_width - 2):
            inventory_window.addch(2, 1 + i, curses.ACS_HLINE)
        # initial tabs display
        x = 2
        for i in range(len(tabs)):
            tab_name = f'[{tabs[i]}]'
            if i == selected_tab:
                inventory_window.addstr(2, x, tab_name, curses.A_REVERSE)
            else:
                inventory_window.addstr(2, x, tab_name)
            x += 2 + len(tab_name)

        choice_id = 0
        page_n = 0
        equip_choice_id = 0
        slots = ['HEAD', 'BODY', 'LEGS', 'ARM1', 'ARM2']
        cursor = 0
        displayed_item_count = win_height - 5

        spell_choice_id = 0
        spell_page_n = 0
        spell_cursor = 0
        spell_display_names = [spell.name for spell in self.player.spells]
        displayed_spell_count = displayed_item_count

        # item description window
        d_window_height = self.HEIGHT
        d_window_width = self.WIDTH - self.window_width - 1
        description_window = curses.newwin(d_window_height, d_window_width, 0, self.window_width + 1)
        desc = []
        if len(display_names) != 0:
            desc = items[cursor + page_n].get_description(d_window_width - 2)
        for i in range(len(desc)):
            description_window.addstr(1 + i, 1, desc[i])
        self.draw_borders(description_window)
        description_window.refresh()

        # initial items display
        for i in range(min(displayed_item_count, len(display_names))):
            if i == cursor:
                inventory_window.addstr(4 + i, 3, f'{display_names[i]}', curses.A_REVERSE)
            else:
                inventory_window.addstr(4 + i, 3, f'{display_names[i]}')
        if len(display_names) > displayed_item_count:
            inventory_window.addch(win_height - 2, 1, curses.ACS_DARROW)
        
        while True:
            key = inventory_window.getch()
            if key == 27: # ESC
                break
            if key == 105: # i
                break
            if key == 259: # UP
                if selected_tab == 0:
                    choice_id -= 1
                    cursor -= 1
                    if cursor < 0:
                        if len(display_names) > displayed_item_count:
                            if page_n == 0:
                                cursor = displayed_item_count - 1
                                choice_id = len(display_names) - 1
                                page_n = len(display_names) - displayed_item_count
                            else:
                                page_n -= 1
                                cursor += 1
                        else:
                            cursor = len(display_names) - 1
                            choice_id = cursor
                if selected_tab == 1:
                    equip_choice_id -= 1
                    if equip_choice_id < 0:
                        equip_choice_id = len(slots) - 1
                if selected_tab == 2:
                    spell_choice_id -= 1
                    spell_cursor -= 1
                    if spell_cursor < 0:
                        if len(spell_display_names) > displayed_spell_count:
                            if spell_page_n == 0:
                                cursor = displayed_spell_count - 1
                                spell_choice_id = len(spell_display_names) - 1
                                spell_page_n = len(display_names) - displayed_spell_count
                            else:
                                spell_page_n -= 1
                                spell_cursor += 1
                        else:
                            spell_cursor = len(spell_display_names) - 1
                            spell_choice_id = spell_cursor
            if key == 258: # DOWN
                if selected_tab == 0:
                    choice_id += 1
                    cursor += 1
                    if len(display_names) > displayed_item_count:
                        if cursor >= displayed_item_count:
                            cursor -= 1
                            page_n += 1
                            if choice_id == len(display_names):
                                cursor = 0
                                page_n = 0
                                choice_id = 0
                    else:
                        if cursor >= len(display_names):
                            cursor = 0
                            choice_id = 0
                if selected_tab == 1:
                    equip_choice_id += 1
                    if equip_choice_id == len(slots):
                        equip_choice_id = 0
                if selected_tab == 2:
                    spell_choice_id += 1
                    spell_cursor += 1
                    if len(spell_display_names) > displayed_spell_count:
                        if spell_cursor >= displayed_spell_count:
                            spell_cursor -= 1
                            spell_page_n += 1
                            if spell_choice_id == len(spell_display_names):
                                spell_cursor = 0
                                spell_page_n = 0
                                spell_choice_id = 0
                    else:
                        if spell_cursor >= len(spell_display_names):
                            spell_cursor = 0
                            spell_choice_id = 0
            if key == 261: # RIGHT
                selected_tab += 1
                if selected_tab == len(tabs):
                    selected_tab = 0
            if key == 260: # LEFT
                selected_tab -= 1
                if selected_tab < 0:
                    selected_tab = len(tabs) - 1
            if key == 10: # ENTER
                if selected_tab == 0: # ITEMS
                    item = items[choice_id]
                    if issubclass(type(item), Items.UsableItem):
                        height = 3
                        width = len('Use') + 2
                        y = 4 + cursor
                        if y + height > self.window_height:
                            y -= height
                        x = 5 + len(display_names[choice_id]) + 1
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        self.draw_borders(options_window)
                        options_window.addstr(1, 1, 'Use', curses.A_REVERSE)
                        options_window.refresh()
                        while True:
                            key = options_window.getch()
                            if key == 27: # ESC
                                break
                            if key == 10: # ENTER
                                item.use(self.player)
                                display_names = self.get_display_names(items)
                                # inventory_window.clear()
                                break
                        
                    if issubclass(type(item), Items.EquipableItem):
                        begin_s = 'Equip to '
                        item_slot = item.slot
                        options = [f'{item_slot}']
                        if item_slot == 'ARM':
                            options = ['ARM1', 'ARM2']
                        height = len(options) + 2
                        width = max([len(s) for s in options]) + 2 + len(begin_s)
                        y = 4 + cursor
                        if y + height > self.window_height:
                            y -= height
                        x = 5 + len(display_names[choice_id]) + 1
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        self.draw_borders(options_window)
                        option_choice_id = 0
                        for i in range(len(options)):
                            if option_choice_id == i:
                                options_window.addstr(1 + i, 1, f'{begin_s}{options[i]}', curses.A_REVERSE)
                            else:
                                options_window.addstr(1 + i, 1, f'{begin_s}{options[i]}')
                        while True:
                            options_key = options_window.getch()
                            options_window.addstr(0, 0, str(options_key))
                            if options_key == 259: # UP
                                option_choice_id -= 1
                                if option_choice_id < 0:
                                    option_choice_id = len(options) - 1
                            if options_key == 258: # DOWN
                                option_choice_id += 1
                                if option_choice_id == len(options):
                                    option_choice_id = 0
                            if options_key == 27: # ESC
                                break
                            if options_key == 10: # ENTER
                                result_slot = options[option_choice_id]
                                item = items[choice_id]
                                if not self.player.meets_requirements(item.requires):
                                    self.message_box('You do not meet the requirements to equip this item', ['Ok'], width=self.window_width - 4, ypos=2, xpos=2)
                                    inventory_window.addstr(1, 1, 'Inventory')
                                    # redraw missing textures
                                    for i in range(win_width - 2):
                                        inventory_window.addch(2, 1 + i, curses.ACS_HLINE)
                                    x = 2
                                    for i in range(len(tabs)):
                                        tab_name = f'[{tabs[i]}]'
                                        if i == selected_tab:
                                            inventory_window.addstr(2, x, tab_name, curses.A_REVERSE)
                                        else:
                                            inventory_window.addstr(2, x, tab_name)
                                        x += 2 + len(tab_name)
                                    break
                                else:
                                    if result_slot == 'ARMS':
                                        self.player.equipment['ARM1'] = choice_id
                                        self.player.equipment['ARM2'] = choice_id
                                    else:
                                        if result_slot.startswith('ARM'):
                                            if self.player.equipment['ARM1'] != None and items[self.player.equipment['ARM1']].slot == 'ARMS':
                                                self.player.equipment['ARM1'] = None
                                                self.player.equipment['ARM2'] = None
                                            else:
                                                if self.player.equipment['ARM1'] == choice_id:
                                                    self.player.equipment['ARM1'] = None
                                                if self.player.equipment['ARM2'] == choice_id:
                                                    self.player.equipment['ARM2'] = None
                                        self.player.equipment[result_slot] = choice_id
                                    display_names = self.get_display_names(items)
                                    break
                            # display
                            for i in range(len(options)):
                                options_window.addstr(1 + i, 1, ' ' * (width - 2))
                            for i in range(len(options)):
                                if option_choice_id == i:
                                    options_window.addstr(1 + i, 1, f'{begin_s}{options[i]}', curses.A_REVERSE)
                                else:
                                    options_window.addstr(1 + i, 1, f'{begin_s}{options[i]}')
                    if issubclass(type(item), Items.SpellBook):
                        s = f'Use (requires INT of {item.int_to_learn})'
                        height = 3
                        width = len(s) + 2
                        y = 4 + cursor
                        if y + height > self.window_height:
                            y -= height
                        x = 5 + len(display_names[choice_id]) + 1
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        self.draw_borders(options_window)
                        options_window.addstr(1, 1, s, curses.A_REVERSE)
                        options_window.refresh()
                        while True:
                            key = options_window.getch()
                            if key == 27: # ESC
                                break
                            if key == 10: # ENTER
                                if self.player.INT >= item.int_to_learn:
                                    self.player.learn_spells(item.spell_names, self.assets_path)
                                    self.player.items.remove(item)
                                    # refresh spell list
                                    spell_choice_id = 0
                                    spell_cursor = 0
                                    spell_page_n = 0
                                    spell_display_names = [spell.name for spell in self.player.spells]
                                    # refresh item list
                                    choice_id = 0
                                    cursor = 0
                                    page_n = 0
                                    items = list(self.player.items)
                                    items += self.player.countable_items
                                    display_names = self.get_display_names(items)
                                    break
                                else:
                                    self.message_box('Insufficient INT to read spellbook!', ['Ok'])
                                    break
                if selected_tab == 1: # EQUIPMENT
                    slot = slots[equip_choice_id]
                    if slot.startswith('ARM') and self.player.equipment['ARM1'] == self.player.equipment['ARM2']:
                        self.player.equipment['ARM1'] = None
                        self.player.equipment['ARM2'] = None
                    else:
                        self.player.equipment[slot] = None
                    display_names = self.get_display_names(items)
                if selected_tab == 2: # SPELLS
                    spell = self.player.spells[spell_choice_id]
                    if issubclass(type(spell), NormalSpell):
                        s = 'Cast (cost: {})'
                        if issubclass(type(spell), BloodSpell):
                            s = s.format(f'{spell.bloodcost} hp')
                        else:
                            s = s.format(f'{spell.manacost} mana')
                        height = 3
                        width = len(s) + 2
                        y = 4 + spell_cursor
                        if y + height > self.window_height:
                            y -= height
                        x = 5 + len(spell_display_names[spell_choice_id]) + 1
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        self.draw_borders(options_window)
                        options_window.addstr(1, 1, s, curses.A_REVERSE)
                        options_window.refresh()
                        while True:
                            key = options_window.getch()
                            if key == 27: # ESC
                                break
                            if key == 10: # ENTER
                                if self.player.can_cast(spell):
                                    response = spell.cast(self.player)
                                    # add response to log
                                    break
                                else:
                                    self.message_box('Can\'t cast spell!', ['Ok'])
                                    break
            # clear the space
            inventory_window.clear()

            inventory_window.addstr(1, 1, 'Inventory')
            self.draw_borders(inventory_window)
            inventory_window.addch(2, 0, curses.ACS_LTEE)
            inventory_window.addch(2, win_width - 1, curses.ACS_RTEE)
            for i in range(win_width - 2):
                inventory_window.addch(2, 1 + i, curses.ACS_HLINE)
            x = 2
            for i in range(len(tabs)):
                tab_name = f'[{tabs[i]}]'
                if i == selected_tab:
                    inventory_window.addstr(2, x, tab_name, curses.A_REVERSE)
                else:
                    inventory_window.addstr(2, x, tab_name)
                x += 2 + len(tab_name)

            # display the tabs
            x = 2
            for i in range(len(tabs)):
                tab_name = f'[{tabs[i]}]'
                if i == selected_tab:
                    inventory_window.addstr(2, x, tab_name, curses.A_REVERSE)
                else:
                    inventory_window.addstr(2, x, tab_name)
                x += 2 + len(tab_name)

            if selected_tab == 0: # items
                # displaying the items
                if len(display_names) > displayed_item_count:
                    if page_n != 0:
                        inventory_window.addch(4, 1, curses.ACS_UARROW)
                    if page_n != len(display_names) - displayed_item_count:
                        inventory_window.addch(win_height - 2, 1, curses.ACS_DARROW)
                for i in range(min(len(display_names), displayed_item_count)):
                    if i == cursor:
                        inventory_window.addstr(4 + i, 3, f'{display_names[i + page_n]}', curses.A_REVERSE)
                    else:
                        inventory_window.addstr(4 + i, 3, f'{display_names[i + page_n]}')
                description_window.clear()
                if len(display_names) != 0:
                    desc = items[cursor + page_n].get_description(self.WIDTH - self.window_width - 3)
                for i in range(len(desc)):
                    description_window.addstr(1 + i, 1, desc[i])
                self.draw_borders(description_window)
                description_window.refresh()
            if selected_tab == 1: # equipment
                for i in range(len(slots)):
                    if i == equip_choice_id:
                        inventory_window.addstr(4 + 2 * i, 3, f'{slots[i]}  -> ', curses.A_REVERSE)
                    else:
                        inventory_window.addstr(4 + 2 * i, 3, f'{slots[i]}  -> ')

                item_name = 'nothing'
                if self.player.equipment['HEAD'] != None:
                    item_name = items[self.player.equipment['HEAD']].name
                inventory_window.addstr(4, 13, item_name)

                item_name = 'nothing'
                if self.player.equipment['BODY'] != None:
                    item_name = items[self.player.equipment['BODY']].name
                inventory_window.addstr(6, 13, item_name)

                item_name = 'nothing'
                if self.player.equipment['LEGS'] != None:
                    item_name = items[self.player.equipment['LEGS']].name
                inventory_window.addstr(8, 13, item_name)
                
                if self.player.equipment['ARM1'] == self.player.equipment['ARM2']:
                    if self.player.equipment['ARM1'] != None:
                        item_name = items[self.player.equipment['ARM1']].name
                        inventory_window.addstr(11, 13, item_name)
                    else:
                        inventory_window.addstr(10, 13, 'nothing')
                        inventory_window.addstr(12, 13, 'nothing')
                else:
                    item_name = 'nothing'
                    if self.player.equipment['ARM1'] != None:
                        item_name = items[self.player.equipment['ARM1']].name
                    inventory_window.addstr(10, 13, item_name)

                    item_name = 'nothing'
                    if self.player.equipment['ARM2'] != None:
                        item_name = items[self.player.equipment['ARM2']].name
                    inventory_window.addstr(12, 13, item_name)

                # desc = []
                # desc = items[cursor + page_n].get_description(self.WIDTH - self.window_width - 3)
                # for i in range(len(desc)):
                #     description_window.addstr(1 + i, 1, desc[i])
                description_window.clear()
                item_id = self.player.equipment[slots[equip_choice_id]]
                if item_id != None:
                    desc = self.player.items[item_id].get_description(self.WIDTH - self.window_width - 3)
                    for i in range(len(desc)):
                        description_window.addstr(1 + i, 1, desc[i])
                self.draw_borders(description_window)
                description_window.refresh()
            if selected_tab == 2: # spells
                if len(spell_display_names) > displayed_spell_count:
                    if spell_page_n != 0:
                        inventory_window.addch(4, 1, curses.ACS_UARROW)
                    if spell_page_n != len(spell_display_names) - displayed_spell_count:
                        inventory_window.addch(win_height - 2, 1, curses.ACS_DARROW)
                for i in range(min(len(spell_display_names), displayed_spell_count)):
                    if i == spell_cursor:
                        inventory_window.addstr(4 + i, 3, f'> {spell_display_names[i + page_n]}')
                    else:
                        inventory_window.addstr(4 + i, 3, f'{spell_display_names[i + page_n]}')
                description_window.clear()
                if len(spell_display_names) != 0:
                    desc = []
                    # add spell description to description window
                for i in range(len(desc)):
                    description_window.addstr(1 + i, 1, desc[i])
                self.draw_borders(description_window)
                description_window.refresh()
        self.stdscr.clear()
        self.draw_info_ui()
        self.draw_player_info()
        self.stdscr.refresh()

    # combat

    def initiate_encounter_with(self, encounter_enemy_code):
        enemy = self.game_room.enemies_data[encounter_enemy_code]
        distance = Utility.distance(self.player_y, self.player_x, enemy.y, enemy.x)
        encounter = CombatEncounter(self.player, enemy, distance, self.HEIGHT, self.WIDTH, self.assets_path)
        encounter.start()

        if self.player.health == 0:
            answer = self.message_box('PLAYER DEAD', ['Load last', 'Back to menu'], width=self.window_width - 4, ypos=2, xpos=2)
            if answer == 'Back to menu':
                self.game_running = False
                return
            self.load_character(self.player.name)
            self.game_running = False
            return
        if enemy.health == 0:
            # self.game_room.enemies_data.pop(encounter_enemy_code, None)
            self.save_enemy_env_vars()
        # clear temporary statuses
        self.player.temporary_statuses = []
        # clean-up
        self.stdscr.clear()
        self.draw_borders(self.tile_window)
        self.draw_info_ui()
        self.draw_player_info()
        self.draw_borders(self.mini_map_window)
        self.mini_map_window.refresh()
        self.stdscr.refresh()
        self.draw_tile_window()
        if self.full_map != None:
            self.draw_mini_map(self.game_room.name)

        self.tile_window.refresh()
        if self.game_room.display_name != '':
            self.draw_room_display_name(self.game_room.display_name)

    # env vars

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
            if var == 'player.gold':
                self.player.gold = real_value
                return False
            self.set_env_var(var, real_value)
            return False
        if command == 'unset':
            var = words[1]
            if var == 'all':
                self.env_vars = dict()
                return False
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
            if var == 'player.max_health':
                self.player.max_health += real_value
                return False
            if var == 'player.mana':
                self.player.add_mana(real_value)
                return False
            if var == 'player.max_mana':
                self.player.max_mana += real_value
                return False
            if var == 'player.gold':
                self.player.gold += real_value
                return False
            if var == 'player.inventory':
                sp = value.split(' ')
                item = None
                if sp[0].isdigit():
                    amount = int(sp[0])
                    item_name = self.get_true_value(' '.join(sp[1:]))
                    item = Items.Item.get_base_items([item_name], f'{self.assets_path}/items.json')[0]
                    item.amount = amount
                else:
                    item = Items.Item.get_base_items([real_value], f'{self.assets_path}/items.json')[0]
                self.player.add_item(item)
                return False
            if var == 'player.spells':
                self.player.learn_spells(real_value, self.assets_path)
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
            if var == 'player.max_health':
                self.player.max_health -= real_value
                return False
            if var == 'player.mana':
                self.player.add_mana(-real_value)
                return False
            if var == 'player.max_mana':
                self.player.max_mana -= real_value
                return False
            if var == 'player.gold':
                self.player.gold -= real_value
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
            self.draw_tile_window()
            self.tile_window.refresh()
            return False
        if command == 'say':
            replies = words[1].split('_')
            var = ' '.join(words[2:])
            real_var = self.get_true_value(var)
            if real_var == None:
                raise Exception(f'ERR: {var} not recognized')
            reply = self.display_dialog(str(real_var), replies)
            self.set_env_var('_reply', reply)
            self.draw_tile_window()
            self.tile_window.refresh()
            return False
        if command == 'move':
            entity_name = words[1]
            move_y = int(words[2])
            move_x = int(words[3])
            if entity_name == 'player':
                self.player_y += move_y
                self.player_x += move_x
            if entity_name == 'camera':
                self.camera_dy += move_y
                self.camera_dx += move_x
            self.tile_window.clear()
            self.draw_tile_window()
            self.tile_window.refresh()
            return False
        if command == 'kill':
            enemy_code = words[1]
            enemy = self.game_room.enemies_data[enemy_code]
            enemy.health = 0
            return False
        if command == 'revive':
            enemy_code = words[1]
            enemy = self.game_room.enemies_data[enemy_code]
            enemy.health = enemy.max_health
            return False
        if command == 'sleep':
            self.draw_tile_window()
            self.tile_window.refresh()
            amount = int(words[1])
            curses.napms(amount)
            return False
        if command == 'clear':
            var = words[1]
            if words[1] == 'player.inventory':
                self.player.items = []
                self.player.countable_items = []
                self.player.equipment['HEAD'] = None
                self.player.equipment['BODY'] = None
                self.player.equipment['LEGS'] = None
                self.player.equipment['ARM1'] = None
                self.player.equipment['ARM2'] = None
                return False
            if words[1] == 'player.spells':
                self.player.spells = []
                return False
            raise Exception(f'ERR: unknown var {var}')
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
        raise Exception(f'ERR: command {command} not recognized')

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
        if s == 'player.max_health':
            return self.player.max_health
        if s == 'player.mana':
            return self.player.mana
        if s == 'player.max_mana':
            return self.player.max_mana
        if s == 'player.name':
            return self.player.name
        if s == 'player.y':
            return self.player_y
        if s == 'player.x':
            return self.player_x
        if s == 'player.gold':
            return self.player.gold
        if s in self.env_vars:
            return self.get_env_var(s)
        ss = s.split('.')
        if ss[0] in self.game_room.chest_contents:
            if ss[1] == 'length':
                items = self.game_room.chest_contents[ss[0]]
                result = 0
                for item in items:
                    key = items[item]
                    if self.get_env_var(key) != True:
                        result += 1
                return result
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
        w = curses.newwin(1, self.window_width - 3, self.window_height, 3)
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