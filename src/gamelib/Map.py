from os import listdir
from os.path import isfile, join, splitext


class Tile:
    def __init__(self, name, char, solid):
        self.name = name
        self.char = char
        self.solid = solid

    def from_char(char):
        if char == ' ' or char == '@':
            return Tile('floor', ' ', False)
        if char == '#':
            return Tile('wall', char, True)
        if char.isdigit() and int(char) >= 0 and int(char) <= 9:
            return DoorTile('door', 'H', False, int(char))
        return Tile('ERR', '!', True)

class DoorTile(Tile):
    def __init__(self, name, char, solid, door_ref):
        super().__init__(name, char, solid)
        self.door_ref = door_ref

class Map:
    def __init__(self, name, height, width, player_spawn_char='@'):
        self.name = name
        self.height = height
        self.width = width
        self.tiles = []
        self.player_spawn_y = 0
        self.player_spawn_x = 0
        self.player_spawn_char = player_spawn_char
        self.door_refs = dict()

    def by_name(name, maps_path, player_spawn_char='@'):
        map_names = [f for f in listdir(maps_path) if isfile(join(maps_path, f)) and splitext(f)[1] == '.map']
        if not f'{name}.map' in map_names:
            raise Exception(f'ERR: map with name {name} not found in {maps_path}')
        raw_data = open(f'{maps_path}/{name}.map', 'r').read()
        map_data = raw_data.split('\n---\n')
        if len(map_data) == 0 or len(map_data) > 2:
            raise Exception(f'ERR: Incorrect map file format. Map name: {name}')
        tile_data = map_data[0]
        if len(map_data) == 2:
            refs_data = map_data[1]
            refs_lines = refs_data.split('\n')
            result = Map.from_str(tile_data, player_spawn_char)
            result.name = name
            result.door_refs = dict()
            for line in refs_lines:
                d = line.split('-')
                result.door_refs[d[0]] = d[1]
        return result


    def from_str(s, player_spawn_char):
        lines = s.split('\n')
        height = len(lines)
        width = len(lines[0])
        result = Map('', height, width)

        result.player_spawn_y = 1
        result.player_spawn_x = 1
        for i in range(height):
            for j in range(width):
                if lines[i][j] == player_spawn_char:
                    result.player_spawn_y, result.player_spawn_x = i, j
        for i in range(height):
            result.tiles += [[]]
            for j in range(width):
                result.tiles[i] += [Tile.from_char(lines[i][j])]
        return result

