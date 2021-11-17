import json
from os import listdir
from os.path import isfile, join, splitext
from gamelib.Entities import Enemy

import gamelib.Items as Items


class Tile:
    def __init__(self, name, char, solid, interactable):
        self.name = name
        self.char = char
        self.solid = solid
        self.interactable = interactable

    def from_info(tile_char, tiles_data, scripts, chest_content_info, config_file):
        if tile_char == ' ' or tile_char == '@':
            return Tile('floor', ' ', False, False)
        if tile_char == '#':
            return Tile('wall', '#', True, False)
        if tile_char in tiles_data.keys():
            tile_name = tiles_data[tile_char][0]
            tile_actual_char = tiles_data[tile_char][1]
            if tile_actual_char == 'space':
                tile_actual_char = ' '
            tile_data = ' '.join(tiles_data[tile_char][2])
            if tile_name == 'door':
                return DoorTile(tile_name, tile_actual_char, False, tile_data)
            if tile_name == 'chest':
                return ChestTile(tile_name, tile_actual_char, True, tile_data)
            if tile_name == 'pressure plate':
                return PressurePlateTile(tile_name, tile_actual_char, tile_data)
            if tile_name == 'torch':
                return TorchTile(tile_name, tile_actual_char, True, False, tile_data)
            if tile_name == 'script tile':
                tile_data = tile_data.split()
                return ScriptTile(tile_data[0], tile_actual_char, tile_data[1])
            if tile_name == 'hidden tile':
                split = tile_data.split()
                signal = split[0]
                if len(split) == 1:
                    return HiddenTile(tile_name, tile_actual_char, True, False, Tile('floor', ' ', False, False), signal)

                actual_tile_tile_char = split[1]
                actual_tile_tiles_data = dict()
                actual_tile_tiles_data[actual_tile_tile_char] = [' '.join(split[2].split('_'))]
                actual_tile_tiles_data[actual_tile_tile_char] += [actual_tile_tile_char]
                actual_tile_tiles_data[actual_tile_tile_char] += [split[3 : len(split)]]
                actual_tile = Tile.from_info(actual_tile_tile_char, actual_tile_tiles_data, scripts, chest_content_info, config_file)
                return HiddenTile(tile_name, tile_actual_char, True, False, actual_tile, signal)
        # in case of unknown tile
        return Tile('ERR', '!', True, False)

class DoorTile(Tile):
    def __init__(self, name, char, solid, info):
        super().__init__(name, char, solid, False)
        self.to = info.split()[0]
        self.door_code = info.split()[1]

class TorchTile(Tile):
    def __init__(self, name, char, solid, interactable, visible_range):
        super().__init__(name, char, solid, interactable)
        self.visible_range = int(visible_range)

class ChestTile(Tile):
    def __init__(self, name, char, solid, chest_code):
        super().__init__(name, char, solid, True)
        self.chest_code = chest_code

class PressurePlateTile(Tile):
    def __init__(self, name, char, script_name):
        super().__init__(name, char, False, False)
        self.script_name = script_name

class HiddenTile(Tile):
    def __init__(self, name, char, solid, interactable, actual_tile, signal):
        super().__init__(name, char, solid, interactable)
        self.actual_tile = actual_tile
        self.signal = signal

class ScriptTile(Tile):
    def __init__(self, name, char, script_name):
        super().__init__(name, char, True, True)
        self.script_name = script_name

class Room:
    def __init__(self, name, height, width, player_spawn_char='@'):
        self.name = name
        self.display_name = ''
        self.height = height
        self.width = width
        self.tiles = []
        self.player_spawn_y = 0
        self.player_spawn_x = 0
        self.visible_range = 0
        self.player_spawn_char = player_spawn_char

    def by_name(name, config_file, env_vars, door_code=None):
        r_p = config_file.get('Rooms path')
        room_names = [f for f in listdir(r_p) if isfile(join(r_p, f)) and splitext(f)[1] == '.room']
        if not f'{name}.room' in room_names:
            raise Exception(f'ERR: room with name {name} not found in {r_p}')
        raw_data = open(f'{r_p}/{name}.room', 'r').read()
        data = raw_data.split('\n---\n')
        if len(data) != 6:
            raise Exception(f'ERR: Incorrect room file format. Room name: {name}')
        layout_data = data[0]
        room_data = data[1]
        tiles_raw_data = data[2]
        scripts_data = data[3]
        chest_content_data = data[4]
        enemies_data = data[5]
        tiles_data = tiles_raw_data.split('\n')
        result = Room.from_str(name, layout_data, tiles_data, room_data, scripts_data, chest_content_data, enemies_data, '@', config_file, door_code, env_vars)
        return result

    def from_str(name, layout_data, raw_tiles_data, room_data, scripts_data, chest_content_data, enemies_data, player_spawn_char, config_file, door_code, env_vars):
        lines = layout_data.split('\n')
        height = len(lines)
        width = len(lines[0])
        result = Room('', height, width)
        result.name = name

        # scripts
        result.scripts = dict()
        for chunk in scripts_data.split('\n\n'):
            l = chunk.split('\n')
            script_name = l[0][:-1]
            script_lines = l[1:]
            result.scripts[script_name] = script_lines
        
        # chest contents
        result.chest_contents = dict()
        for chunk in chest_content_data.split('\n\n'):
            l = chunk.split('\n')
            chest_code = l[0][:-1]
            raw_chest_content = l[1:]
            d = dict()
            for i in range(len(raw_chest_content)):
                raw_item = raw_chest_content[i]
                sri = raw_item.split(' ')
                item = None
                if sri[0].isdigit():
                    amount = int(sri[0])
                    item_name = ' '.join(sri[1:])
                    if item_name == 'Gold':
                        item = Items.GoldPouch()
                    else:
                        item = Items.Item.get_base_items([item_name], config_file.get('Items path'))[0]
                    item.amount = amount
                    d[item] = f'{chest_code}_{i}'
                else: 
                    item_name = ' '.join(sri)
                    item = Items.Item.get_base_items([item_name], config_file.get('Items path'))[0]
                    d[item] = f'{chest_code}_{i}'
                if item == None:
                    data = ' '.join(sri)
                    raise Exception(f'ERR: item with data {data} not parsable')
            result.chest_contents[chest_code] = d
        
        # enemy data
        result.enemies_data = dict()
        if len(enemies_data) != 0:
            for chunk in enemies_data.split('\n\n'):
                l = chunk.split('\n')
                enemy_code = l[0][:-1]
                enemy_data = l[1:]
                y = -1
                x = -1
                enemy = Enemy()
                for line in enemy_data:
                    d = line.split('=')
                    if d[0] == 'e_type':
                        enemy = Enemy.from_enemy_name(d[1], config_file)
                    if d[0] == 'y':
                        y = int(d[1])
                    if d[0] == 'x':
                        x = int(d[1])
                if y == -1:
                    raise Exception(f'ERR: y not defined when defining enemy')
                if x == -1:
                    raise Exception(f'ERR: x not defined when defining enemy')
                enemy.y = y
                enemy.x = x
                var_start = f'enemies_{name}_{enemy_code}_'
                # fill the values from env_vars
                # y pos
                var = f'{var_start}y'
                if var in env_vars:
                    enemy.y = env_vars[var]
                env_vars[var] = enemy.y
                # x pos
                var = f'{var_start}x'
                if var in env_vars:
                    enemy.x = env_vars[var]
                env_vars[var] = enemy.x

                enemy.max_health = enemy.health
                # health
                var = f'{var_start}health'
                if var in env_vars:
                    enemy.health = env_vars[var]
                env_vars[var] = enemy.health

                enemy.max_mana = enemy.mana
                # mana
                var = f'{var_start}mana'
                if var in env_vars:
                    enemy.mana = env_vars[var]
                env_vars[var] = enemy.mana
                if enemy.health > 0:
                    result.enemies_data[enemy_code] = enemy

        tiles_data = dict()
        # parse tile data
        for data_line in raw_tiles_data:
            if data_line == '':
                continue
            d = data_line.split()
            key = d[0]
            char = d[1]
            tile_name = ' '.join(d[2].split('_'))
            tiles_data[key] = [tile_name, char, d[3 : len(d)]]

        # file the layout
        result.tiles = []
        for i in range(height):
            result.tiles += [[]]
            for j in range(width):
                result.tiles[i] += [Tile.from_info(lines[i][j], tiles_data, result.scripts, result.chest_contents, config_file)]

        # find the player spawn point
        if not door_code:
            result.player_spawn_y = 1
            result.player_spawn_x = 1
            for i in range(height):
                for j in range(width):
                    if lines[i][j] == player_spawn_char:
                        result.player_spawn_y, result.player_spawn_x = i, j
        else:
            for i in range(height):
                for j in range(width):
                    if isinstance(result.tiles[i][j], DoorTile) and result.tiles[i][j].door_code == door_code or (isinstance(result.tiles[i][j], HiddenTile) and isinstance(result.tiles[i][j].actual_tile, DoorTile) and result.tiles[i][j].actual_tile.door_code == door_code):
                        result.player_spawn_y, result.player_spawn_x = i, j


        split = room_data.split()
        for line in split:
            s = line.split('=')
            if s[0] == 'visible_range':
                result.visible_range = int(s[1])
            if s[0] == 'display_name':
                result.display_name = s[1]
        return result