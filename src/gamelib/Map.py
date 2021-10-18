import json
from os import listdir
from os.path import isfile, join, splitext

import gamelib.Items as Items


class Tile:
    def __init__(self, name, char, solid):
        self.name = name
        self.char = char
        self.solid = solid


class DoorTile(Tile):
    def __init__(self, name, char, solid, to):
        super().__init__(name, char, solid)
        self.to = to

class ChestTile(Tile):
    def __init__(self, name, char, solid, names, assets_path):
        super().__init__(name, char, solid)
        self.items = Items.Item.get_base_items(names, f'{assets_path}/items.json')

class Map:
    def __init__(self, name, height, width, player_spawn_char='@'):
        self.name = name
        self.height = height
        self.width = width
        self.tiles = []
        self.player_spawn_y = 0
        self.player_spawn_x = 0
        self.player_spawn_char = player_spawn_char

    def by_name(name, maps_path, assets_path, player_spawn_char='@'):
        map_names = [f for f in listdir(maps_path) if isfile(join(maps_path, f)) and splitext(f)[1] == '.map']
        if not f'{name}.map' in map_names:
            raise Exception(f'ERR: map with name {name} not found in {maps_path}')
        raw_data = open(f'{maps_path}/{name}.map', 'r').read()
        map_data = raw_data.split('\n---\n')
        if len(map_data) != 2:
            raise Exception(f'ERR: Incorrect map file format. Map name: {name}')
        layout_data = map_data[0]
        tiles_raw_data = map_data[1]
        tiles_data = tiles_raw_data.split('\n')
        result = Map.from_str(layout_data, tiles_data, player_spawn_char, assets_path)
        result.name = name
        return result

    def from_str(layout_data, raw_tiles_data, player_spawn_char, assets_path):
        lines = layout_data.split('\n')
        height = len(lines)
        width = len(lines[0])
        result = Map('', height, width)
        
        # find the player spawn point
        result.player_spawn_y = 1
        result.player_spawn_x = 1
        for i in range(height):
            for j in range(width):
                if lines[i][j] == player_spawn_char:
                    result.player_spawn_y, result.player_spawn_x = i, j
        
        tiles_data = dict()
        # parse tile data
        for data_line in raw_tiles_data:
            d = data_line.split()
            key = d[0]
            tile_name = d[1]
            tiles_data[key] = [tile_name, d[2 : len(d)]]

        # file the layout
        result.tiles = []
        for i in range(height):
            result.tiles += [[]]
            for j in range(width):
                tile_char = lines[i][j]
                if tile_char == ' ' or tile_char == '@':
                    result.tiles[i] += [Tile('floor', ' ', False)]
                    continue
                if tile_char == '#':
                    result.tiles[i] += [Tile('wall', '#', True)]
                    continue
                if tile_char in tiles_data.keys():
                    tile_name = tiles_data[tile_char][0]
                    tile_data = ' '.join(tiles_data[tile_char][1])
                    if tile_name == 'door':
                        result.tiles[i] += [DoorTile(tile_name, tile_char, False, tile_data)]
                        continue
                    if tile_name == 'chest':
                        result.tiles[i] += [ChestTile(tile_name, tile_char, True, tile_data, assets_path)]
                        continue
                # in case of unknown tile
                result.tiles[i] += [Tile('ERR', '!', True)]

                    

        return result

