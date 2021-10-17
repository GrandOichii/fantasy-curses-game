import json
from os import listdir
from os.path import isfile, join

def save(player, saves_path):
    data = dict()
    data['player'] = player.json()
    
    open(f'{saves_path}/{player.name}.save', 'w').write(json.dumps(data))

def save_file_exists(saves_path, name):
    files = [f for f in listdir(saves_path) if isfile(join(saves_path, f))]
    return f'{name}.save' in files