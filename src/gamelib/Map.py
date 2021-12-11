import curses

from gamelib.Room import Room

class Map:
    def __init__(self, path: str):
        text = open(path, 'r').read()
        pretty_tiles = {
            '-': curses.ACS_HLINE,
            '|': curses.ACS_VLINE,
            '+': curses.ACS_PLUS,
            'r': curses.ACS_ULCORNER,
            'L': curses.ACS_LLCORNER,
            '\\': curses.ACS_URCORNER,
            '/': curses.ACS_LRCORNER,
            'T': curses.ACS_TTEE,
            '}': curses.ACS_LTEE,
            'I': curses.ACS_BTEE,
            '{': curses.ACS_RTEE
        }

        self.tiles = []
        tile_data = text.split('\n---\n')[0]
        room_name_data = text.split('\n---\n')[1]

        tile_lines = tile_data.split('\n')
        room_name_lines = room_name_data.split('\n')

        self.height = len(tile_lines)
        self.width = len(tile_lines[0])

        self._map_coords = dict()

        for i in range(self.height):
            self.tiles += [[]]
            split = room_name_lines[i].split('|')
            for j in range(self.width):
                char = pretty_tiles[tile_lines[i][j]]
                room = split[j].split(' ')[0]
                var = split[j].split(' ')[1]
                self.tiles[i] += [Tile(char, room, var)]

                self._map_coords[room] = [i, j]

    def get_mini_tiles(self, room_name: str, env_vars: dict, h: int, w: int, hh: int, hw: int):
        if not room_name in self._map_coords.keys():
            raise Exception(f'ERR: room {room_name} not in map coords')
        y, x = self._map_coords[room_name]
        result = []
        for i in range(h):
            result += [[]]
            for j in range(w):
                char = ' '
                modi = y + i - hh
                modj = x + j - hw
                if modi >= 0 and modj >= 0 and modi < self.height and modj < self.width:
                    tile = self.tiles[modi][modj]
                    if tile.var in env_vars.keys() and env_vars[tile.var] == True:
                        char = tile.char
                result[i] += [char]
        return result

class Tile:
    def __init__(self, char: str, room: Room, var: str):
        self.char = char
        self.room = room
        self.var = var

