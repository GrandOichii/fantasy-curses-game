import curses
import curses.textpad as textpad
import json
from math import sqrt
import os
from Configuraion import ConfigFile

from ncursesui.Elements import Menu, Window, Button, UIElement, Widget, TextField, WordChoice, Separator
from ncursesui.Utility import calc_pretty_bars, draw_separator, message_box, cct_len, draw_borders, drop_down_box, put, MULTIPLE_ELEMENTS, show_controls_window, str_smart_split
from gamelib.Cooking import CursesCooking

# import gamelib.Entities as Entities
from gamelib.Entities import *
import gamelib.Spells as Spells
import gamelib.Room as Room
import gamelib.Items as Items
import gamelib.Map as Map
import gamelib.SaveFile as SaveFile

# from gamelib.Entities import Player, Enemy
from gamelib.Combat import CombatEncounter
from gamelib.Trade import Trade

def distance(ay: int, ax: int, by: int, bx: int):
    return sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by))

class GameLog:
    MAX_SIZE = 20
    def __init__(self):
        self.messages = []

    def add(self, messages: list):
        for i in range(len(messages)):
            messages[i] = '- ' + messages[i]
        self.messages += messages

    def length(self):
        return len(self.messages)

    def get_splits(self, max_width: int):
        splits = []
        for message in self.messages:
            splits += str_smart_split(message, max_width)
        return splits

    def get_last(self, max_width: int, amount: int):
        # optimize
        return self.get_splits(max_width)[-amount:]

class Game:
    controls = {
        "Move": "ARROW KEYS",
        "Move diagonally": "y, u, b, n",
        "Open inventory": "i",
        "Open command line": "~",
        "Open tile description mode": "x",
        "Start combat": "c",
        "Open full log": "L",
        "Exit and save": "Q",
        "Interact": "E"
    }

    def __init__(self, parent : Window, character_name: str, config_file: ConfigFile):
        self.parent = parent
        
        self.window = parent.get_window()
        self.character_name = character_name
        self.config_file = config_file

        self.max_name_len = 20

        data = SaveFile.load(character_name, self.config_file.get('Saves path'))
        if data == -1:
            sp = self.config_file.get('Saves path')
            raise Exception(f'ERR: save file of character with name {character_name} not found in {sp}')
        self.player = Player.from_json(data['player'], self.config_file)
        self.env_vars = data['env_vars']
        self.last_command = ''
        self.game_room = Room.Room.by_name(data['room_name'], self.config_file, self.env_vars)

        self.player_y, self.player_x = self.game_room.player_spawn_y, self.game_room.player_spawn_x
        if 'player_y' in data:
            self.player_y = data['player_y']
        if 'player_x' in data:
            self.player_x = data['player_x']

        # set some values
        self.tile_window_height = self.parent.HEIGHT * 5 // 6
        if self.tile_window_height % 2 == 0: self.tile_window_height -= 1
        self.tile_window_width = self.parent.WIDTH - self.max_name_len - 8

        self.tile_window_width -= 2

        self.player_info_window_height = 13
        self.player_info_window_width = self.parent.WIDTH - self.tile_window_width - 1

        self.camera_dy = 0
        self.camera_dx = 0

        self.MINI_MAP_HEIGHT = 7
        self.MINI_MAP_WIDTH = 7

        self.log_window_height = self.parent.HEIGHT - self.tile_window_height
        self.log_window_width = self.tile_window_width
        self.game_log = GameLog()
        self.game_log.messages = data['game_log']

        self.mid_y = self.tile_window_height // 2 
        self.mid_x = self.tile_window_width // 2
            
    def start(self):
        self.window.clear()
        self.window.refresh()

        # room tile window
        self.tile_window = curses.newwin(self.tile_window_height, self.tile_window_width, 0, 0)
        self.tile_window.keypad(1)
        draw_borders(self.tile_window)
        # self.tile_window.nodelay(True)
        # self.tile_window.timeout(self.game_speed)

        # player info window
        self.player_info_window = curses.newwin(self.player_info_window_height, self.player_info_window_width, 0, self.tile_window_width + 1)
        
        # mini map window
        self.mini_map_window = curses.newwin(self.MINI_MAP_HEIGHT + 2, self.MINI_MAP_WIDTH + 2, 13, self.parent.WIDTH - self.MINI_MAP_WIDTH - 2)

        # log window
        self.log_window = curses.newwin(self.log_window_height, self.log_window_width, self.tile_window_height, 0)

        self.full_map = None
        if self.config_file.has('Map path'):
            self.full_map = Map.Map(self.config_file.get('Map path'))
        
        self.draw()

        if '_load' in self.game_room.scripts:
            self.exec_script('_load', self.game_room.scripts)

        # main game loop
        self.main_game_loop()

    # main loop methods

    def main_game_loop(self):
        entered_room = False
        encounter_ready, encounter_enemy_code = self.check_for_encounters()
        self.game_running = True
        update_entities = True

        while self.game_running:
            # check if there is a tick script in current room
            if '_tick' in self.game_room.scripts:
                self.exec_script('_tick', self.game_room.scripts)

            # get player input
            key = self.window.getch()
            if key == 81 and self.tile_message_box('Are you sure you want to quit? (Progress will be saved)', ['No', 'Yes']) == 'Yes':
                self.save_enemy_env_vars()
                SaveFile.save(self.player, self.game_room.name, self.config_file.get('Saves path'), player_y=self.player_y, player_x=self.player_x, env_vars=self.env_vars, game_log_messages=self.game_log.messages)
                break
            if key == 126: # ~
                update_entities = False
                command = self.get_terminal_command()
                self.exec_line(command, self.game_room.scripts)
            if key == 63:
                show_controls_window(self.parent, Game.controls)
                self.draw()
                continue
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
            # open big log window
            if key == 76: # L
                self.open_big_log_window()
                continue
            # interact
            if key == 101: # e
                interactable_tiles = self.get_interactable_tiles(self.player_y, self.player_x)
                # if len(interactable_tiles) == 0:
                #     message_box(self.parent, 'No tiles to interact with nearby!', ['Ok'],width=self.tile_window_width - 4, ypos=2, xpos=2)
                # else:
                interact_key = self.get_prompt('Interact where?')
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
                    if isinstance(i_tile, Room.CookingPotTile):
                        self.initiate_cooking()
                    if isinstance(i_tile, Room.HiddenTile) and isinstance(i_tile.actual_tile, Room.CookingPotTile):
                        self.initiate_cooking()
                    if isinstance(i_tile, Room.ScriptTile):
                        self.exec_script(i_tile.script_name, self.game_room.scripts)
                    if isinstance(i_tile, Room.HiddenTile) and isinstance(i_tile.actual_tile, Room.ScriptTile):
                        self.exec_script(i_tile.actual_tile.script_name, self.game_room.scripts)
                else:
                    self.game_log.add(['Can\'t interact with that'])
            # open inventory
            if key == 105: # i
                self.draw_inventory()
                update_entities = False
            # initiate combat
            if key == 99: # c
                if encounter_ready:
                    self.initiate_encounter_with(encounter_enemy_code)
                else:
                    self.tile_message_box('You are not within range to attack anybody!', ['Ok'])
            # enter tile description mode
            if key == 120: # x
                update_entities = False
            if self.game_running:
                tile = self.game_room.tiles[self.player_y][self.player_x]
                if isinstance(tile, Room.DoorTile) and entered_room:
                    entered_room = False
                    destination_room = tile.to
                    door_code = tile.door_code
                    self.set_env_var('_last_door_code', door_code)
                    self.game_room = Room.Room.by_name(destination_room, self.config_file, door_code=door_code, env_vars=self.env_vars)
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

                if update_entities:
                    self.update_entities()
                update_entities = True

                # check if encounters are available

                self.draw()
                encounter_ready, encounter_enemy_code = self.check_for_encounters()
                
                if key == 120: # x
                    self.tile_description_mode()    

    def tile_message_box(self, message: str, choices: list, additional_lines: list=[]):
        return message_box(self.parent, message, choices, additional_lines=additional_lines, width=self.tile_window_width - 4, ypos=2, xpos=2)

    def display_error(self, error_message: str):
        return message_box(self.parent, error_message, ['Ok'], width=self.tile_window_width - 4, ypos=2, xpos=2, border_color='red-black')

    def notify(self, message: str, author: str):
        min_height = 5
        window_width = self.tile_window_width - 2
        messages = str_smart_split(message, window_width - 2)
        window_height = max(len(messages) + 2, min_height)
        window_y = self.tile_window_height - window_height - 1
        window_x = 2
        window = curses.newwin(window_height, window_width, window_y, window_x)
        draw_borders(window)
        if author:
            put(window, 0, 1, author)
        for i in range(len(messages)):
            put(window, 1 + i, 1, messages[i])
        continue_str = '<   #black-white V#normal    >'
        cs_x = window_width // 2 - cct_len(continue_str) // 2
        put(window, window_height - 1, cs_x, continue_str)
        while True:
            key = window.getch()
            if key == 10:
                break
        self.draw()

    def check_for_encounters(self):
        encounter_ready = False
        enemy_code = None
        min_d = -1
        min_enemy_code = None
        for enemy_code in self.game_room.enemies_data:
            enemy = self.game_room.enemies_data[enemy_code]
            if self.can_see_enemy(enemy):
            # if enemy.health > 0:
                d = distance(enemy.y, enemy.x, self.player_y, self.player_x)
                player_range = self.player.get_range()
                if d <= player_range:
                    if min_d == -1 or d < min_d:
                        min_d = d
                        min_enemy_code = enemy_code
        if min_enemy_code != None:
            enemy = self.game_room.enemies_data[min_enemy_code]
            encounter_ready = True
            s = f'[ Press [c] to initiate combat with #red-black {enemy.name} #normal ]'
            y = self.tile_window_height - 2
            x = self.tile_window_width // 2 - cct_len(s) // 2
            put(self.tile_window, y, x, s)
            self.tile_window.refresh()
        return (encounter_ready, enemy_code)    

    def update_entities(self):
        self.player.check_items()
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

    def display_dialog(self, message: str, replies: list):
        borders_color_pair = 'cyan-black'
        width = self.tile_window_width - 2
        height = self.tile_window_height // 2

        lines = str_smart_split(message, width - 2)
        name = '???'
        if '_say_name' in self.env_vars:
            name = self.get_env_var('_say_name')

        w = curses.newwin(height - 1, width, height + 1, 2)
        draw_borders(w, borders_color_pair)
        w.keypad(1)
        put(w, 0, 1, f'#green-black {name}')

        for i in range(len(lines)):
            put(w, 1 + i, 1, lines[i])
        draw_separator(w, height - len(replies) - 3, borders_color_pair)
        for i in range(len(replies)):
            put(w, height - len(replies) - 2 + i, 3, replies[i])
        choice_i = 0
        key = -1
        while True:
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
                    put(w, height - len(replies) - 2 + i, 1, '> ')
                else:    
                    put(w, height - len(replies) - 2 + i, 1, '  ')
            key = w.getch()
        return replies[choice_i]

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
            if key in [56, 259] and cursor_map_y != 0 and distance(cursor_map_y - 1, cursor_map_x, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_y -= 1
                cursor_map_y -= 1
            # South
            if key in [50, 258] and cursor_map_y != self.game_room.height - 1 and distance(cursor_map_y + 1, cursor_map_x, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_y += 1
                cursor_map_y += 1
            # West
            if key in [52, 260] and cursor_map_x != 0 and distance(cursor_map_y, cursor_map_x - 1, self.player_y, self.player_x) < self.game_room.visible_range:
                cursor_x -= 1
                cursor_map_x -= 1
            # East
            if key in [54, 261] and cursor_map_x != self.game_room.width - 1 and distance(cursor_map_y, cursor_map_x + 1, self.player_y, self.player_x) < self.game_room.visible_range:
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
                if enemy.health > 0:
                    y = enemy.y + self.mid_y - self.player_y
                    x = enemy.x + self.mid_x - self.player_x
                    if distance(self.player_y, self.player_x, enemy.y, enemy.x) < self.game_room.visible_range:
                        if y == cursor_y and x == cursor_x:
                            self.tile_window.addch(y, x, enemy.char, curses.A_REVERSE)
                            display_name = enemy.name
                        else:
                            self.tile_window.addch(y, x, enemy.char)
            if len(display_name) != 0:
                self.tile_window.addstr(1, 1, f'[{display_name}]')
            draw_borders(self.tile_window)
        # clean-up
        self.draw()

    def get_interactable_tiles(self, y: int, x: int):
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

    def interact_with_chest(self, chest_tile: Room.ChestTile):
        items_dict = self.game_room.container_info[chest_tile.container_code]

        item_names = []
        codes = []
        for item in items_dict:
            if isinstance(item, Items.CountableItem):
                # item is countable item
                amount = self.get_env_var(items_dict[item])
                if amount == None or amount > 0:
                    item_names += [item.get_cct_display_text()]
                    codes += [items_dict[item]]
            elif self.get_env_var(items_dict[item]) != True:
                # item is normal item
                item_names += [item.get_cct_display_text()]
                codes += [items_dict[item]]

        if len(item_names) == 0:
            message_box(self.parent, 'Chest is empty.', ['Ok'])
            return
        results = drop_down_box(item_names, 4, self.mid_y, self.mid_x + 3, MULTIPLE_ELEMENTS)
        if len(results) == 0:
            return
        items = list(items_dict.keys())
        # remove taken items
        for i in results:
            if isinstance(items[i], Items.CountableItem):
                self.set_env_var(codes[i], 0)
            else:
                self.set_env_var(codes[i], True)
        # add items to inventory
        for i in results:
            self.player.add_item(items[i])

        # clear the leftovers from the drop down box borders
        for i in range(self.parent.HEIGHT):
            self.window.addstr(i, self.tile_window_width + 1, ' ')

    def initiate_cooking(self):
        # self.tile_message_box('#red-black Cooking is not implemented', ['Ok'])
        cooking = CursesCooking(self.parent, self.player, self.config_file)
        cooking.start()
        self.player.check_items()
        self.game_log.add(cooking.get_log_messages())

    def get_display_names(self, items: list):
        result = []
        for i in range(len(items)):
            item = items[i]
            line = item.get_cct_display_text()
            if issubclass(type(item), Items.EquipableItem):
                for s in self.player.equipment:
                    if self.player.equipment[s] == i:
                        if item.slot == 'ARMS':
                            line += f' -> ARMS'
                        else:
                            line += f' -> {s}'
                        break
            result += [line]
        return result

    def draw_inventory(self):
        items = list(self.player.items)
        items += self.player.countable_items

        display_names = self.get_display_names(items)

        win_height = self.tile_window_height
        win_width = self.tile_window_width
        inventory_window = curses.newwin(win_height, win_width, 0, 0)
        inventory_window.keypad(1)

        selected_tab = 0
        tabs = ['Items', 'Equipment', 'Spells']

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
        d_window_height = self.parent.HEIGHT - self.player_info_window_height
        d_window_width = self.parent.WIDTH - self.tile_window_width - 1
        description_window = curses.newwin(d_window_height, d_window_width, self.player_info_window_height, self.tile_window_width + 1)

        description_limit = d_window_height - 2
        description_page = 0        
        
        while True:
            # display
            draw_borders(inventory_window)
            put(inventory_window, 0, 1, '#magenta-black Inventory')
            # display the tabs
            draw_separator(inventory_window, 1)
            x = 2
            for i in range(len(tabs)):
                tab_name = f'[{tabs[i]}]'
                if i == selected_tab:
                    put(inventory_window, 1, x, tab_name, curses.A_REVERSE)
                else:
                    put(inventory_window, 1, x, tab_name)
                x += 2 + len(tab_name)

            # display items
            if selected_tab == 0: # items
                # displaying the items
                if len(display_names) > displayed_item_count:
                    if page_n != 0:
                        inventory_window.addch(3, 1, curses.ACS_UARROW)
                    if page_n != len(display_names) - displayed_item_count:
                        inventory_window.addch(win_height - 2, 1, curses.ACS_DARROW)
                for i in range(min(len(display_names), displayed_item_count)):
                    attr = curses.A_REVERSE if i == cursor else 0
                    put(inventory_window, 3 + i, 3, f'{display_names[i + page_n]}', attr)
                description_window.clear()
                if len(display_names) != 0:
                    desc = items[cursor + page_n].get_description(d_window_width - 2)
                else:
                    desc = []
            if selected_tab == 1: # equipment
                for i in range(len(slots)):
                    if i == equip_choice_id:
                        inventory_window.addstr(3 + 2 * i, 3, f'{slots[i]}  -> ', curses.A_REVERSE)
                    else:
                        inventory_window.addstr(3 + 2 * i, 3, f'{slots[i]}  -> ')

                item_name = 'nothing'
                if self.player.equipment['HEAD'] != None:
                    item_name = items[self.player.equipment['HEAD']].name
                inventory_window.addstr(3, 13, item_name)

                item_name = 'nothing'
                if self.player.equipment['BODY'] != None:
                    item_name = items[self.player.equipment['BODY']].name
                inventory_window.addstr(5, 13, item_name)

                item_name = 'nothing'
                if self.player.equipment['LEGS'] != None:
                    item_name = items[self.player.equipment['LEGS']].name
                inventory_window.addstr(7, 13, item_name)
                
                if self.player.equipment['ARM1'] == self.player.equipment['ARM2']:
                    if self.player.equipment['ARM1'] != None:
                        item_name = items[self.player.equipment['ARM1']].name
                        inventory_window.addstr(10, 13, item_name)
                    else:
                        inventory_window.addstr(9, 13, 'nothing')
                        inventory_window.addstr(11, 13, 'nothing')
                else:
                    item_name = 'nothing'
                    if self.player.equipment['ARM1'] != None:
                        item_name = items[self.player.equipment['ARM1']].name
                    inventory_window.addstr(9, 13, item_name)

                    item_name = 'nothing'
                    if self.player.equipment['ARM2'] != None:
                        item_name = items[self.player.equipment['ARM2']].name
                    inventory_window.addstr(11, 13, item_name)
                description_window.clear()
                item_id = self.player.equipment[slots[equip_choice_id]]
                if item_id != None:
                    desc = self.player.items[item_id].get_description(d_window_width - 2)
                else:
                    desc = []
            if selected_tab == 2: # spells
                if len(spell_display_names) > displayed_spell_count:
                    if spell_page_n != 0:
                        inventory_window.addch(3, 1, curses.ACS_UARROW)
                    if spell_page_n != len(spell_display_names) - displayed_spell_count:
                        inventory_window.addch(win_height - 2, 1, curses.ACS_DARROW)
                for i in range(min(len(spell_display_names), displayed_spell_count)):
                    attr = curses.A_REVERSE if i == spell_cursor else 0
                    inventory_window.addstr(3 + i, 3, f'{spell_display_names[i + page_n]}', attr)
                description_window.clear()
                if len(spell_display_names) != 0:
                    desc = self.player.spells[spell_cursor + spell_page_n].get_description(d_window_width - 2)
                else:
                    desc = []

            # display description
            draw_borders(description_window)
            put(description_window, 0, 1, '#magenta-black Description')
            first = 0
            last = len(desc) - 1
            if len(desc) > description_limit:
                first = description_page
                last = description_page + description_limit - 1
            for i in range(first, last + 1):
                put(description_window, 1 + i - first, 1, desc[i])
            if len(desc) > description_limit:
                if description_page != 0:
                    description_window.addch(1, d_window_width - 1, curses.ACS_UARROW)
                if description_page != len(desc) - description_limit:
                    description_window.addch(d_window_height - 2, d_window_width - 1, curses.ACS_DARROW)
            description_window.refresh()

            # display player info
            self.draw_player_info()
            self.player_info_window.refresh()

            # key handling
            key = inventory_window.getch()
            if key == 27: # ESC
                break
            if key == 105: # i
                break
            if key == 259: # UP
                description_limit = d_window_height - 2
                description_page = 0  
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
                description_limit = d_window_height - 2
                description_page = 0  
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
                        y = 3 + cursor
                        if y + height > self.tile_window_height:
                            y -= height
                        x = 3 + cct_len(display_names[choice_id])
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        draw_borders(options_window)
                        options_window.addstr(1, 1, 'Use', curses.A_REVERSE)
                        options_window.refresh()
                        while True:
                            key = options_window.getch()
                            if key == 27: # ESC
                                break
                            if key == 10: # ENTER
                                # TO-DO: fix this
                                messages = item.use(self.player)
                                if item.amount < 1:
                                    choice_id = 0
                                    cursor = 0
                                    page_n = 0
                                self.game_log.add(messages)
                                self.player.check_items()
                                items = list(self.player.items)
                                items += self.player.countable_items
                                display_names = self.get_display_names(items)
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
                        if y + height > self.tile_window_height:
                            y -= height
                        x = 4 + cct_len(display_names[choice_id])
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        draw_borders(options_window)
                        option_choice_id = 0
                        options_key = -1
                        while True:
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
                                    self.tile_message_box('You do not meet the requirements to equip this item', ['Ok'])
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
                            options_key = options_window.getch()
                    if issubclass(type(item), Items.SpellBook):
                        s = f'Use (requires INT of {item.int_to_learn})'
                        height = 3
                        width = len(s) + 2
                        y = 4 + cursor
                        if y + height > self.tile_window_height:
                            y -= height
                        x = 4 + len(display_names[choice_id])
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        draw_borders(options_window)
                        options_window.addstr(1, 1, s, curses.A_REVERSE)
                        options_window.refresh()
                        while True:
                            key = options_window.getch()
                            if key == 27: # ESC
                                break
                            if key == 10: # ENTER
                                if self.player.INT >= item.int_to_learn:
                                    self.player.learn_spells(item.spell_names, self.config_file.get('Spells path'))
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
                                    message_box(self.parent, 'Insufficient INT to read spellbook!', ['Ok'])
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
                    if issubclass(type(spell), Spells.NormalSpell):
                        s = 'Cast (cost: {})'
                        if issubclass(type(spell), Spells.BloodSpell):
                            s = s.format(f'{spell.bloodcost} hp')
                        else:
                            s = s.format(f'{spell.manacost} mana')
                        height = 3
                        width = len(s) + 2
                        y = 4 + spell_cursor
                        if y + height > self.tile_window_height:
                            y -= height
                        x = 5 + len(spell_display_names[spell_choice_id]) + 1
                        options_window = curses.newwin(height, width, y, x)
                        options_window.keypad(1)
                        draw_borders(options_window)
                        options_window.addstr(1, 1, s, curses.A_REVERSE)
                        options_window.refresh()
                        while True:
                            key = options_window.getch()
                            if key == 27: # ESC
                                break
                            if key == 10: # ENTER
                                if self.player.can_cast(spell):
                                    messages = spell.cast(self.player)
                                    self.game_log.add(messages)
                                    break
                                else:
                                    message_box(self.parent, 'Can\'t cast spell!', ['Ok'])
                                    break
                self.draw_log_window()
                self.log_window.refresh()
            if key == 60: # <
                if len(desc) > description_limit:
                    description_page -= 1
                    if description_page < 0:
                        description_page = 0
            if key == 62: # >
                if len(desc) > description_limit:
                    description_page += 1
                    if description_page > len(desc) - description_limit:
                        description_page = len(desc) - description_limit
            
            # clear the space
            inventory_window.clear()
  
        self.window.clear()
        self.window.refresh()
        self.draw()

    def get_prompt(self, message: str):
        message = '[#green-black {}#normal ]'.format(message)
        put(self.tile_window, 1, self.mid_x - cct_len(message) // 2, message)
        self.tile_window.refresh()
        key = self.window.getch()
        return key
    
    def open_big_log_window(self):
        b_l_window_height = self.parent.HEIGHT - 6
        b_l_window_width = self.parent.WIDTH // 2

        b_l_window_y = self.parent.HEIGHT // 2 - b_l_window_height // 2
        b_l_window_x = self.parent.WIDTH // 2 - b_l_window_width // 2

        big_log_window = curses.newwin(b_l_window_height, b_l_window_width, b_l_window_y, b_l_window_x)
        big_log_window.keypad(1)

        splits = self.game_log.get_splits(b_l_window_width - 2)

        limit = b_l_window_height - 2
        page = 0

        while True:
            # display
            big_log_window.clear()
            draw_borders(big_log_window)
            put(big_log_window, 0, 1, '#magenta-black Log')
            first = 0
            last = len(splits) - 1
            if len(splits) > limit:
                first = page
                last = page + limit - 1
            y = 1
            for i in range(first, last + 1):
                put(big_log_window, y, 1, splits[i])
                y += 1
            if len(splits) > limit:
                if page != 0:
                    big_log_window.addch(1, b_l_window_width - 1, curses.ACS_UARROW)
                if page != len(splits) - limit:
                    big_log_window.addch(b_l_window_height - 2, b_l_window_width - 1, curses.ACS_DARROW)

            # key handling
            key = big_log_window.getch()
            if key == 27: # ESC
                break
            if key == 259: # UP
                if len(splits) > limit:
                    page -= 1
                    if page < 0:
                        page = 0
            if key == 258: # DOWN
                if len(splits) > limit:
                    page += 1
                    if page > len(splits) - limit:
                        page = len(splits) - limit
            
        self.window.clear()
        self.window.refresh()
        self.draw()
    
    def initiate_trade(self, vendor_name: str, gold_var: str, container_code: str):
        items_dict = self.game_room.container_info[container_code]
        items = [key for key in items_dict]
        normal_items, countable_items = Items.Item.separate_items(items)
        
        # normal items
        vendor_items = []
        for item in normal_items:
            if self.get_env_var(items_dict[item]) != True:
                vendor_items += [item]

        # countable items
        vendor_countable_items = []
        for item in countable_items:
            if self.get_env_var(items_dict[item]) != 0:
                c_item = item.copy()
                real_amount = self.get_env_var(items_dict[item])
                c_item.amount = real_amount if real_amount != None else item.amount
                vendor_countable_items += [c_item]

        trade = Trade(self.parent, self.player, vendor_name, self.get_env_var(gold_var), vendor_items, vendor_countable_items)   
        state = trade.start()
        if not state:
            self.window.clear()
            self.window.refresh()
            self.draw()
            return

        # set gold values
        self.set_env_var(gold_var, trade.get_vendor_final_gold())
        self.player.gold = trade.get_player_final_gold()

        # remove sold items
        for i in range(len(trade.sold_item_ids) - 1, -1, -1):
            i_id = trade.sold_item_ids[i]
            self.player.remove_item(i_id)

        # remove sold countable items
        for key in trade.sold_countable_item_amounts:
            amount = trade.sold_countable_item_amounts[key]
            self.player.countable_items[key].amount -= amount

        # add bought items
        for i in trade.bought_item_ids:
            self.player.add_item(trade.vendor_items[i])

        # add bought countable items
        for key in trade.bought_countable_item_amounts:
            amount = trade.bought_countable_item_amounts[key]
            if amount > 0:
                item = trade.vendor_countable_items[key].copy()
                item.amount = amount
                self.player.add_item(item)

        # manage bought item codes
        for i in trade.bought_item_ids:
            code = items_dict[vendor_items[i]]
            self.set_env_var(code, True)

        codes = list(items_dict.values())
        # manage bought countable item amounts
        for key in trade.bought_countable_item_amounts:
            item = trade.vendor_countable_items[key]
            code = codes[key + len(normal_items)]
            self.set_env_var(code, item.amount)
            
        # clean-up
        self.window.clear()
        self.window.refresh()
        self.draw()
    
    def enemy_is_lit(self, enemy: Enemy):
        for i in range(self.game_room.height):
            for j in range(self.game_room.width):
                r = 0
                if isinstance(self.game_room.tiles[i][j], Room.TorchTile):
                    r = self.game_room.tiles[i][j].visible_range
                if isinstance(self.game_room.tiles[i][j], Room.HiddenTile) and self.get_env_var(self.game_room.tiles[i][j].signal) == True and isinstance(self.game_room.tiles[i][j].actual_tile, Room.TorchTile):
                    # !!! BIG ISSUE !!! either rework hidden tiles, or make a work-around
                    r = self.game_room.tiles[i][j].actual_tile.visible_range
                if distance(i, j, enemy.y, enemy.x) < r:
                    return True
        return distance(self.player_y, self.player_x, enemy.y, enemy.x) < self.game_room.visible_range

    def can_see_enemy(self, enemy: Enemy):
        # enemy.health > 0 and sqrt((self.player_y - enemy.y) * (self.player_y - enemy.y) + (self.player_x - enemy.x) * (self.player_x - enemy.x)) < self.game_room.visible_range:
        return enemy.health > 0 and not (enemy.y == -1 and enemy.x == -1) and self.enemy_is_lit(enemy)

    # combat

    def initiate_encounter_with(self, encounter_enemy_code: str, player_is_attacking: bool=True):
        enemy = self.game_room.enemies_data[encounter_enemy_code]
        d = distance(self.player_y, self.player_x, enemy.y, enemy.x)
        encounter = None
        if player_is_attacking:
            encounter = CombatEncounter(self.parent, self.player, enemy, d, self.config_file)
            self.game_log.add([f'#green-black {self.player.name} #normal attacks #red-black {enemy.name}#normal !'])
        else:
            encounter = CombatEncounter(self.parent, enemy, self.player, d, self.config_file)
            self.game_log.add([f'#red-black {enemy.name} #normal attacks #green-black {self.player.name}!'])
        rewards = encounter.start()
        
        if self.player.health == 0:
            answer = self.tile_message_box('PLAYER DEAD', ['Back to menu'])
            self.game_running = False
            return
        if enemy.health == 0:
            # self.game_room.enemies_data.pop(encounter_enemy_code, None)
            self.save_enemy_env_vars()

        # clear temporary statuses
        self.player.temporary_statuses = []

        # add stuff to game log
        self.game_log.add([f'#green-black {self.player.name} #normal defeats #red-black {enemy.name}#normal !'])
        game_log_messages = []
        if 'gold' in rewards:
            gold = rewards['gold']
            game_log_messages += [f'#green-black {self.player.name} #normal looted #yellow-black {gold} #normal gold from #red-black {enemy.name}#normal .']
        message = '#green-black {} #normal looted {} #normal from {}#normal .'
        for reward in rewards['items'] + rewards['countable_items']:
            game_log_messages += [message.format(self.player.name, reward.get_cct_display_text(), enemy.name)]
        self.game_log.add(game_log_messages)

        # clean-up
        self.window.clear()
        self.window.refresh()
        self.draw()

        if self.game_room.display_name != '':
            self.draw_room_display_name(self.game_room.display_name)

    # draw

    def draw(self):
        self.draw_player_info()
        self.draw_tile_window()
        self.draw_mini_map(self.game_room.name)
        self.draw_log_window()
        if self.game_room.display_name != '':
            self.draw_room_display_name(self.game_room.display_name)

        self.tile_window.refresh()
        self.player_info_window.refresh()
        self.mini_map_window.refresh()
        self.log_window.refresh()

    def draw_log_window(self):
        self.log_window.clear()
        draw_borders(self.log_window)
        put(self.log_window, 0, 1, '#magenta-black Log')
        max_amount = self.log_window_height - 2
        messages = self.game_log.get_last(self.log_window_width - 2, max_amount)
        for i in range(len(messages)):
            put(self.log_window, 1 + i, 1, messages[i])

    def draw_player_info(self):
        # check player mana
        if self.player.mana > self.player.get_max_mana():
            self.player.mana = self.player.get_max_mana()
        # check player health
        if self.player.health > self.player.get_max_health():
            self.player.health = self.player.get_max_health()

        self.player_info_window.clear()
        draw_borders(self.player_info_window)
        put(self.player_info_window, 0, 1, '#magenta-black Player info')

        fill = lambda value, max_length: ' ' * (max_length - len(str(value))) + str(value)
        y = 1
        x = 1

        # display name
        put(self.player_info_window, y + 0, x, f'Name: #green-black {self.player.name}')
        # display class
        put(self.player_info_window, y + 1, x, f'Class: #green-black {self.player.class_name}')
        # display gold
        put(self.player_info_window, y + 2, x, f'Gold: #yellow-black {self.player.gold}')
        # display armor rating
        put(self.player_info_window, y + 3, x, f'Armor: #white-blue {self.player.get_armor()}')
        # display health
        health_str = 'Health: #red-black {}#normal (#red-black {}#normal /#red-black {}#normal )'.format(calc_pretty_bars(self.player.health, self.player.get_max_health(), 10), fill(self.player.health, 3), fill(self.player.get_max_health(), 3))
        put(self.player_info_window, y + 4, x, health_str)
        # display mana
        mana_str = '  Mana: #cyan-black {}#normal (#cyan-black {}#normal /#cyan-black {}#normal )'.format(calc_pretty_bars(self.player.mana, self.player.get_max_mana(), 10), fill(self.player.mana, 3), fill(self.player.get_max_mana(), 3))
        put(self.player_info_window, y + 5, x, mana_str)
        # display strength
        put(self.player_info_window, y + 7, x, f'#black-red STR: #normal {fill(self.player.STR, 3)}')
        # display dexterity
        put(self.player_info_window, y + 8, x, f'#black-green DEX: #normal {fill(self.player.DEX, 3)}')
        # display intelligence
        put(self.player_info_window, y + 9, x, f'#black-cyan INT: #normal {fill(self.player.INT, 3)}')

    def draw_tile_window(self):
        self.tile_window.clear()
        draw_borders(self.tile_window)
        put(self.tile_window, 0, 1, '#magenta-black Room display')
        self.draw_tiles(self.player_y, self.player_x, self.game_room.visible_range)
        self.draw_torches()
        # last to display
        real_mid_y = self.mid_y + self.camera_dy
        real_mid_x = self.mid_x - self.camera_dx
        if real_mid_y > 0 and real_mid_y < self.tile_window_height - 1 and real_mid_x > 0 and real_mid_x < self.tile_window_width - 1:
            put(self.tile_window, real_mid_y, real_mid_x, '#green-black @')
        if self.full_map != None:
            self.draw_mini_map(self.game_room.name)
        self.draw_enemies()

    def draw_mini_map(self, room_name: str):
        self.mini_map_window.clear()
        draw_borders(self.mini_map_window)
        put(self.mini_map_window, 0, 1, '#magenta-black Minimap')
        if self.full_map == None:
            return
        hh = self.MINI_MAP_HEIGHT // 2
        hw = self.MINI_MAP_WIDTH // 2
        mini_map_tiles = self.full_map.get_mini_tiles(room_name, self.env_vars, self.MINI_MAP_HEIGHT, self.MINI_MAP_WIDTH, hh, hw)
        for i in range(self.MINI_MAP_HEIGHT):
            for j in range(self.MINI_MAP_WIDTH):
                if i == hh and j == hw:
                    self.mini_map_window.addch(1 + i, 1 + j, mini_map_tiles[i][j], curses.A_REVERSE)
                else:
                    self.mini_map_window.addch(1 + i, 1 + j, mini_map_tiles[i][j])

    def draw_room_display_name(self, display_name: str):
        h = 3
        w = len(display_name) + 2
        y = self.tile_window_height - 3 - 1
        x = self.tile_window_width - w -1
        win = curses.newwin(h, w, y, x)
        win.addstr(1, 1, display_name)
        draw_borders(win)

    def draw_tiles(self, y: int, x: int, visible_range: int):
        mid_y = self.mid_y - self.player_y + y + self.camera_dy
        mid_x = self.mid_x - self.player_x + x - self.camera_dx
        for i in range(max(1, mid_y - visible_range), min(self.tile_window_height - 1, mid_y + visible_range + 1)):
            for j in range(max (1, mid_x - visible_range), min(self.tile_window_width - 1, mid_x + visible_range + 1)):
                if distance(i, j, mid_y, mid_x) < visible_range:
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

    def draw_torches(self):
        for i in range(self.game_room.height):
            for j in range(self.game_room.width):
                if isinstance(self.game_room.tiles[i][j], Room.TorchTile):
                    self.draw_tiles(i, j, self.game_room.tiles[i][j].visible_range)
                if isinstance(self.game_room.tiles[i][j], Room.HiddenTile) and self.get_env_var(self.game_room.tiles[i][j].signal) == True and isinstance(self.game_room.tiles[i][j].actual_tile, Room.TorchTile):
                    # !!! BIG ISSUE !!! either rework hidden tiles, or make a work-around
                    self.draw_tiles(i, j, self.game_room.tiles[i][j].actual_tile.visible_range)

    def draw_enemies(self):
        for enemy in list(self.game_room.enemies_data.values()):
            if self.can_see_enemy(enemy):
                y = enemy.y + self.mid_y - self.player_y
                x = enemy.x + self.mid_x - self.player_x
                self.tile_window.addch(y, x, enemy.char)

    # env vars

    def set_env_var(self, var: str, value):
        self.env_vars[var] = value

    def get_env_var(self, var: str):
        if not var in self.env_vars.keys():
            return None
        var = self.env_vars[var]
        return var

    def exec_line(self, line: str, scripts: dict):
        if line[0] == '#':
            return False
        words = line.split()
        command = words[0]
        self.last_command = command
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
                self.player.health = min(real_value, self.player.get_max_health())                        
                return False
            if var == 'player.mana':
                self.player.mana = min(real_value, self.player.get_max_mana())                        
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
            if var == 'player.inventory' or var == 'player.items':
                sp = value.split(' ')
                item = None
                if sp[0].isdigit():
                    amount = int(sp[0])
                    item_name = self.get_true_value(' '.join(sp[1:]))
                    item = Items.Item.get_base_items([item_name], self.config_file.get('Items path'))[0]
                    item.amount = amount
                else:
                    item = Items.Item.get_base_items([real_value], self.config_file.get('Items path'))[0]
                self.player.add_item(item)
                return False
            if var == 'player.spells':
                self.player.learn_spells([real_value], self.config_file.get('Spells path'))
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
            choices = words[1].split('|')
            var = ' '.join(words[2:])
            real_var = self.get_true_value(var)
            if real_var == None:
                raise Exception(f'ERR: {var} not recognized')  
            answer = self.tile_message_box(str(real_var), choices)
            self.set_env_var('_mb_result', answer)
            self.draw_tile_window()
            self.tile_window.refresh()
            return False
        if command == 'notify':
            var = ' '.join(words[1:])
            message = self.get_true_value(var)
            author = self.get_env_var('_notify_name')
            self.notify(message, author)
            return False
        if command == 'say':
            raw_replies = words[1].split('|')
            replies = []
            for r in raw_replies:
                replies += [' '.join(r.split('_'))]
            var = ' '.join(words[2:])
            real_var = self.get_true_value(var)
            if real_var == None:
                raise Exception(f'ERR: {var} not recognized')
            interlocutor_name = self.get_env_var('_say_name')
            self.game_log.add(['#green-black {}#normal : #cyan-black \"{}\"'.format('???' if interlocutor_name == None else interlocutor_name, real_var)])
            self.draw_log_window()
            self.log_window.refresh()
            reply = self.display_dialog(str(real_var), replies)
            self.set_env_var('_reply', reply)
            self.game_log.add([f'#green-black {self.player.name}#normal : #cyan-black \"{reply}\"'])
            self.draw_tile_window()
            self.tile_window.refresh()
            self.draw_log_window()
            self.log_window.refresh()
            return False
        if command == 'log':
            s = ' '.join(words[1:])
            message = self.get_true_value(s)
            self.game_log.add([message])
            self.draw_log_window()
            self.log_window.refresh()
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
            enemy.health = enemy.get_max_health()
            return False
        if command == 'sleep':
            self.draw_tile_window()
            self.tile_window.refresh()
            amount = int(words[1])
            curses.napms(amount)
            return False
        if command == 'clear':
            var = words[1]
            if words[1] == 'player.inventory' or words[1] == 'player.items':
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
            # conditionals
            if words[1] in ['==', '>', '<', '>=', '<=']:
                var1 = words[0]
                var2 = ' '.join(words[2:words.index('then')])
                real_var1 = self.get_true_value(var1)
                real_var2 = self.get_true_value(var2)
                if words[1] == '==':
                    do_if = real_var1 == real_var2
                if words[1] == '!=':
                    do_if = real_var1 != real_var2
                if words[1] == '>':
                    do_if = real_var1 > real_var2
                if words[1] == '<':
                    do_if = real_var1 > real_var2
                if words[1] == '>=':
                    do_if = real_var1 >= real_var2
                if words[1] == '<=':
                    do_if = real_var1 >= real_var2
            if words[1] == 'in':
                item_name = self.get_env_var(words[0])
                container_code = words[2]
                if container_code == 'player.inventory' or container_code == 'player.items':
                    do_if = False
                    for item in self.player.items:
                        if item.name == item_name:
                            do_if = True
                            break
                    for item in self.player.countable_items:
                        if item.name == item_name:
                            do_if = True
                            break
                else:
                    items = self.game_room.container_info[container_code]
                    do_if = False
                    for item in items:
                        if item.name == item_name:
                            code = items[item]
                            code_value = self.get_env_var(code)
                            if code_value == None: 
                                do_if = True
                            elif code_value != True and code_value != 0:
                                do_if = True
            if reverse != do_if:
                return self.exec_line(' '.join(words[words.index('then') + 1:]), scripts)
            return False
        if command == 'fight':
            enemy_code = words[1]
            self.initiate_encounter_with(enemy_code, False)
            return self.player.health == 0
        if command == 'trade':
            gold_var = words[1]
            container_code = words[2]
            vendor_name = '???'
            if '_vendor_name' in self.env_vars:
                vendor_name = self.get_env_var('_vendor_name')
            self.initiate_trade(vendor_name, gold_var, container_code)
            return False
        if command == 'draw':
            self.draw()
            return False
        if command == 'stop':
            return True
        if command == 'return':
            var = ' '.join(words[1:])
            real_var = self.get_true_value(var)
            self.set_env_var('_return_value', real_var)
            return False
        raise Exception(f'ERR: command {command} not recognized')

    def get_true_value(self, s: str):
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
            return self.player.get_max_health()
        if s == 'player.mana':
            return self.player.mana
        if s == 'player.max_mana':
            return self.player.get_max_mana()
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
        if ss[0] in self.game_room.container_info:
            if ss[1] == 'length':
                items = self.game_room.container_info[ss[0]]
                result = 0
                for item in items:
                    key = items[item]
                    if self.get_env_var(key) != 0 and self.get_env_var(key) != True:
                        result += 1
                return result
        return None

    def exec_script(self, name: str, scripts: dict):
        script = scripts[name]
        for script_line in script:
            if script_line == '':
                continue
            quit = self.exec_line(script_line, scripts)
            if self.last_command == 'return':
                self.last_command = ''
                return False
            if quit:
                return True
            
    def get_terminal_command(self):
        self.window.addstr(self.tile_window_height, 1, '> ')
        self.window.refresh()
        w = curses.newwin(1, self.tile_window_width - 3, self.tile_window_height, 3)
        curses.curs_set(1)
        w.keypad(1)
        box = textpad.Textbox(w)
        box.edit(self._terminal_command_validator)
        result = box.gather()
        curses.curs_set(0)
        w.clear()
        w.refresh()
        self.window.addstr(self.tile_window_height, 1, '  ')
        self.window.refresh()
        return result

    def _terminal_command_validator(self, ch: str):
        if ch in [127, 8]:
            return 8
        return ch

class GameWindow(Window):   
    def __init__(self, window, config_file: ConfigFile):
        self.universal_menu_controls = {
            "Close app": "ESC", 
            "Click button": "ENTER", 
            "Move between buttons": "UP/DOWN"
        }
        super().__init__(window)
        if self.WIDTH < 135:
            message_box(self, f'Termainal window too small, you may encounter bugs', ['Ok'])
        self.debug = False
        self.config_file = config_file
        self.starting_room = 'index'
        if config_file.has('Starting room'):
            self.starting_room = config_file.get('Starting room')
        self.game_speed = 200

        self.create_folders()

    def initUI(self):
        # menu init
        self.main_menu = Menu(self, '#red-black Fantasy #cyan-black Curses #magenta-black Game')
        self.main_menu.bottom_description = ''
        self.main_menu.controls = self.universal_menu_controls
        self.main_menu.bottom_description = '#black-cyan Click #black-yellow ?#black-cyan  for controls'

        self.credits_menu = Menu(self, '#yellow-black Credits')
        self.credits_menu.bottom_description = 'https://github.com/GrandOichii/fantasy-curses-game'
        self.credits_menu.controls = self.universal_menu_controls

        self.character_creation_menu = Menu(self, '#cyan-black Character creation')
        self.character_creation_menu.bottom_description = 'Create your character!'

        # elements init
        self.new_game_button = Button(self, 'New game', self.to_character_creation_action)
        self.new_game_button.set_focused(True)
        self.new_game_button.set_pos(1, 1)

        self.load_game_button = Button(self, 'Load', self.load_game_action)
        self.load_game_button.set_pos(2, 1)

        self.settings_button = Button(self, 'Settings', self.to_settings_action)
        self.settings_button.set_pos(3, 1)

        self.credits_button = Button(self, 'Credits', self.to_credits_action)
        self.credits_button.set_pos(4, 1)

        self.exit_button = Button(self, 'Exit', self.exit)
        self.exit_button.set_pos(5, 1)

        back_to_main_button = Button(self, 'Back', self.to_main_menu_action)
        back_to_main_button.set_focused(True)
        back_to_main_button.set_pos(1, 1)

        name_text_widget = Widget(self)
        name_text_widget.add_element(UIElement(self, 'Name: '))
        self.name_text_field = TextField(self, '', 20)
        name_text_widget.add_element(self.name_text_field)
        name_text_widget.focused_element_id = 1
        name_text_widget.set_pos(1, 1)
        name_text_widget.set_focused(True)

        class_widget = Widget(self)
        class_widget.add_element(UIElement(self, 'Class:'))
        self.class_choice = WordChoice(self, ['Warrior', 'Mage', 'Rogue'])
        class_widget.add_element(self.class_choice)
        class_widget.focused_element_id = 1
        class_widget.set_pos(2, 1)

        create_button = Button(self, 'Create', self.create_character_action)
        create_button.set_pos(4, 1)

        cancel_button = Button(self, 'Cancel', self.to_main_menu_action)
        cancel_button.set_pos(5, 1)

        # next prev setting
        self.new_game_button.prev = self.exit_button
        self.new_game_button.next = self.load_game_button

        self.new_game_button.prev = self.exit_button
        self.new_game_button.next = self.load_game_button

        self.load_game_button.prev = self.new_game_button
        self.load_game_button.next = self.settings_button

        self.settings_button.prev = self.load_game_button
        self.settings_button.next = self.credits_button

        self.credits_button.prev = self.settings_button
        self.credits_button.next = self.exit_button
        
        self.exit_button.prev = self.credits_button
        self.exit_button.next = self.new_game_button

        name_text_widget.prev = cancel_button
        name_text_widget.next = class_widget

        class_widget.prev = name_text_widget
        class_widget.next = create_button

        create_button.prev = class_widget
        create_button.next = cancel_button
        
        cancel_button.prev = create_button
        cancel_button.next = name_text_widget
        
        # add elements to menus
        self.main_menu.add_element(self.new_game_button)
        self.main_menu.add_element(self.load_game_button)
        self.main_menu.add_element(self.settings_button)
        self.main_menu.add_element(self.credits_button)
        self.main_menu.add_element(self.exit_button)

        self.character_creation_menu.add_element(name_text_widget)
        self.character_creation_menu.add_element(class_widget)
        self.character_creation_menu.add_element(Separator(self, 3))
        self.character_creation_menu.add_element(create_button)
        self.character_creation_menu.add_element(cancel_button)

        self.credits_menu.add_element(back_to_main_button)

        self.current_menu = self.main_menu

    def handle_key(self, key: int):
        if key == 27:
            self.exit()

    # actions

    def to_credits_action(self):
        self.current_menu = self.credits_menu

    def to_main_menu_action(self):
        self.current_menu = self.main_menu

    def to_settings_action(self):
        message_box(self, '#red-black Not implemented yet!', ['Ok'])
        return
        # TO-DO: change to settings window

    def to_character_creation_action(self):
        self.character_creation_menu.get_current_tab().unfocus_all()
        self.character_creation_menu.get_current_tab().focus(0)

        self.name_text_field.text = ''
        self.name_text_field.cursor = 0

        self.class_choice.choice = 0

        self.current_menu = self.character_creation_menu

    def create_character_action(self):
        character_name = self.name_text_field.text
        character_class = self.class_choice.get_selected_value()
        if message_box(self, 'Is this ok?',  ['Yes', 'No'], additional_lines=[f'Name: #cyan-black {character_name}', f'Class: #cyan-black {character_class}']) == 'No':
            return
        # create the character
        character_class = character_class.lower()
        player = Player()
        player.name = character_name
        data = json.loads(open('assets/class_schemas.json').read())
        if not character_class in data:
            raise Exception(f'ERR: Class {character_class} not found in assets')
        player.load_class(data[character_class], 'assets/items.json')
        already_exists = SaveFile.save_file_exists(self.config_file.get('Saves path'), player.name)
        if already_exists and message_box(self, f'File with name {player.name} already exists, override?', ['No', 'Yes']) == 'No':
            return
        SaveFile.save(player, self.starting_room, self.config_file.get('Saves path'))
        self.load_character(player.name)

    def load_game_action(self):
        if SaveFile.count_saves(self.config_file.get('Saves path')) == 0:
            message_box(self, 'No save files detected!', ['Ok'])
            self.current_menu = self.main_menu
            return
        save_desc, corrupt_files = SaveFile.save_descriptions(self.config_file.get('Saves path'))
        for cor in corrupt_files:
            if message_box(self, f'Character {cor} seems to be corrupt, delete file?', ['No', 'Yes']) == 'Yes':
                SaveFile.delete_save_file(cor, self.config_file.get('Saves path'))

        # ch_names = SaveFile.character_names(self.config_file.get('Saves path'))
        load_menu = Menu(self, '#cyan-black Load character')
        load_menu.bottom_description = 'Load a previous character'
        load_menu.controls = self.universal_menu_controls


        label = UIElement(self, 'Load character:')
        label.set_pos(1, 1)
        load_menu.add_element(label)

        # first button
        first_button = Button(self, f'#cyan-black {save_desc[0]}', self.load_character_pick_action)
        first_button.set_focused(True)
        first_button.set_pos(2, 2)
        load_menu.add_element(first_button)

        last_button = first_button

        # other buttons
        i = 1
        for i in range(1, len(save_desc)):
            new_button = Button(self, f'#cyan-black {save_desc[i]}', self.load_character_pick_action)
            new_button.set_pos(2 + i, 2)

            new_button.prev = last_button
            last_button.next = new_button

            load_menu.add_element(new_button)
            last_button = new_button
        
        # back to main button
        button = Button(self, 'Back', self.to_main_menu_action)
        button.set_pos(4 + i, 1)
        last_button.next = button
        button.prev = last_button
        button.next = first_button
        first_button.prev = button

        load_menu.add_element(Separator(self, 3 + i))
        load_menu.add_element(button)

        self.current_menu = load_menu

    def load_character_pick_action(self):
        names = SaveFile.character_names(self.config_file.get('Saves path'))
        name = names[self.current_menu.get_current_tab().get_focused_element_id() - 1]
        response = message_box(self, f'Load character {name}?', ['Load', 'Delete', 'Cancel'])
        if response == 'Cancel':
            return
        if response == 'Load':
            self.load_character(name)
        if response == 'Delete' and message_box(self, f'Delete character {name}? (Permanent)', ['No', 'Yes']) == 'Yes':
            SaveFile.delete_save_file(name, self.config_file.get('Saves path'))
            self.load_game_action()

    # utility methods

    def load_character(self, character_name: str):
        game = Game(self, character_name, self.config_file)
        game.start()

        self.current_menu = self.main_menu

    def create_folders(self):
        # create saves folder
        if not os.path.exists(self.config_file.get('Saves path')):
            try:
                os.mkdir(self.config_file.get('Save path'))
            except Exception as ex:
                print('ERROR - Could not create saves folder')
                print(ex)
                input() # ???
                exit()