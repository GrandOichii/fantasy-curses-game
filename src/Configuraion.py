class ConfigItem:
    def __init__(self, name: str, value):
        self.name = name
        self.value = value

class ConfigFile:
    def __init__(self, path: str):
        self.path = path

        self.config_items = []
        data = open(path, 'r').read()
        for line in data.split('\n'):
            s = line.split('=')
            name = s[0]
            value = s[1]
            self.config_items += [ConfigItem(name, value)]

    def get(self, name: str):
        for item in self.config_items:
            if item.name == name:
                return item.value
        raise Exception(f'ERR: config item {name} not recognized')

    def has(self, name: str):
        for item in self.config_items:
            if item.name == name:
                return True
        return False