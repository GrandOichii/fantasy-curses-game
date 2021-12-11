import json
from os import listdir, remove
from os.path import isfile, join, splitext

from gamelib.Entities import Player

def save(player: Player, room_name: str, saves_path: str, player_y: int=-1, player_x: int=-1, env_vars: dict=dict(), game_log_messages: list[str]=[]):
    data = dict()
    data['player'] = player.json()
    data['room_name'] = room_name
    data['env_vars'] = env_vars
    data['game_log'] = game_log_messages
    if player_y != -1:
        data['player_y'] = player_y
    if player_x != -1:
        data['player_x'] = player_x
    open(f'{saves_path}/{player.name}.save', 'w').write(json.dumps(data, indent=4, sort_keys=True))

def load(name: str, saves_path: str):
    files = _get_save_file_names(saves_path)
    if not f'{name}.save' in files:
        return -1
    return json.loads(open(f'{saves_path}/{name}.save', 'r').read())

def save_file_exists(saves_path: str, name: str):
    files = _get_save_file_names(saves_path)
    return f'{name}.save' in files

def save_descriptions(saves_path: str):
    result = []
    files = _get_save_file_names(saves_path)
    corrupt_files = []
    for file in files:
        try:
            data = json.loads(open(f'{saves_path}/{file}', 'r').read())['player']
            name = data['name']
            cl = data['class_name']
            result += [f'{name} ({cl})']
        except Exception:
            corrupt_files += [splitext(file)[0]]
            
    return result, corrupt_files

def count_saves(saves_path: str):
    return len(listdir(saves_path))

def _get_save_file_names(saves_path: str):
    return [f for f in listdir(saves_path) if isfile(join(saves_path, f)) and splitext(f)[1] == '.save']

def character_names(saves_path: str):
    return [splitext(f)[0] for f in listdir(saves_path) if isfile(join(saves_path, f)) and splitext(f)[1] == '.save']

def delete_save_file(name: str, saves_path: str):
    if not name in character_names(saves_path):
        raise Exception(f'ERR: No save file {name}.save, could not delete')
    remove(f'{saves_path}/{name}.save')
    