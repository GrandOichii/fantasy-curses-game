import json
from os import listdir, remove
from os.path import isfile, join, splitext
from posixpath import split

def save(player, room_name, saves_path, player_y=-1, player_x=-1, env_vars=dict()):
    data = dict()
    data['player'] = player.json()
    data['room_name'] = room_name
    data['env_vars'] = env_vars
    if player_y != -1:
        data['player_y'] = player_y
    if player_x != -1:
        data['player_x'] = player_x
    open(f'{saves_path}/{player.name}.save', 'w').write(json.dumps(data, indent=4, sort_keys=True))

def load(name, saves_path):
    files = _get_save_file_names(saves_path)
    if not f'{name}.save' in files:
        return -1
    return json.loads(open(f'{saves_path}/{name}.save', 'r').read())

def save_file_exists(saves_path, name):
    files = _get_save_file_names(saves_path)
    return f'{name}.save' in files

def save_descriptions(saves_path):
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

def count_saves(saves_path):
    return len(listdir(saves_path))

def _get_save_file_names(saves_path):
    return [f for f in listdir(saves_path) if isfile(join(saves_path, f)) and splitext(f)[1] == '.save']

def character_names(saves_path):
    return [splitext(f)[0] for f in listdir(saves_path) if isfile(join(saves_path, f)) and splitext(f)[1] == '.save']

def delete_save_file(name, saves_path):
    if not name in character_names(saves_path):
        raise Exception(f'ERR: No save file {name}.save, could not delete')
    remove(f'{saves_path}/{name}.save')
    