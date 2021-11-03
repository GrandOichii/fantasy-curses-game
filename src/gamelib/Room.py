import json
from os import listdir
from os.path import isfile, join, splitext

import gamelib.Items as Items


class Tile:
    def __init__(self, name, char, solid, interactable):
        self.name = name
        self.char = char
        self.solid = solid
        self.interactable = interactable

    def from_info(tile_char, tiles_data, scripts, chest_content_info, assets_path):
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
                actual_tile = Tile.from_info(actual_tile_tile_char, actual_tile_tiles_data, scripts, chest_content_info, assets_path)
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

    def by_name(name, rooms_path, assets_path, door_code=None):
        room_names = [f for f in listdir(rooms_path) if isfile(join(rooms_path, f)) and splitext(f)[1] == '.room']
        if not f'{name}.room' in room_names:
            raise Exception(f'ERR: room with name {name} not found in {rooms_path}')
        raw_data = open(f'{rooms_path}/{name}.room', 'r').read()
        data = raw_data.split('\n---\n')
        if len(data) != 5:
            raise Exception(f'ERR: Incorrect room file format. Room name: {name}')
        layout_data = data[0]
        room_data = data[1]
        tiles_raw_data = data[2]
        scripts_data = data[3]
        chest_content_data = data[4]
        tiles_data = tiles_raw_data.split('\n')
        result = Room.from_str(layout_data, tiles_data, room_data, scripts_data, chest_content_data, '@', assets_path, door_code)
        result.name = name
        return result

    def from_str(layout_data, raw_tiles_data, room_data, scripts_data, chest_content_data, player_spawn_char, assets_path, door_code):
        lines = layout_data.split('\n')
        height = len(lines)
        width = len(lines[0])
        result = Room('', height, width)
        result.scripts = dict()
        for chunk in scripts_data.split('\n\n'):
            l = chunk.split('\n')
            script_name = l[0][:-1]
            script_lines = l[1:]
            result.scripts[script_name] = script_lines
        result.chest_contents = dict()
        for chunk in chest_content_data.split('\n\n'):
            l = chunk.split('\n')
            chest_code = l[0][:-1]
            raw_chest_content = l[1:]
            d = dict()
            for raw_item in raw_chest_content:
                sri = raw_item.split(' ')
                item_code = sri[-1]
                item_name = ' '.join(sri[:-1])
                item = Items.Item.get_base_items([item_name], f'{assets_path}/items.json')[0]
                d[item] = f'{chest_code}_{item_code}'
            result.chest_contents[chest_code] = d

        
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
                result.tiles[i] += [Tile.from_info(lines[i][j], tiles_data, result.scripts, result.chest_contents, assets_path)]

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