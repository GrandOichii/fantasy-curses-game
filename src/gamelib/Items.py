import json

class Item:
    def __init__(self):
        self.name = ''

    def get_base_item(name, path):
        data = json.loads(open(path).read())
        for type in data:
            for item in data[type]:
                if item['name'] == name:
                    return Item.from_json(item, type)
        return 'ERR'


    
    def from_json(js, type='item'):
        result = Item()
        if type == 'melee':
            result = MeleeWeapon()
        if type == 'ranged':
            result = RangedWeapon()
        if type == 'armor':
            result = Armor()
        if type == 'ammo':
            result = Ammo()

        result.__dict__ = js
        return result

    def __str__(self):
        result = f'Name: {self.name}'
        return result

class Armor(Item):
    def __init__(self):
        super().__init__()
        self.mods = {}
        self.slot = ''
        self.requires = {}

    def __str__(self):
        result = super().__str__()
        result += f'\nSlot: {self.slot}'
        if len(self.mods) != 0:
            result += f'\nModifiers:'
            for key in self.mods:
                result += f'\n  {key}: {self.mods[key]}'
        if len(self.requires) != 0:
            result += f'\nRequirements:'
            for key in self.requires:
                result += f'\n  {key}: {self.requires[key]}'
        return result

class Ammo(Item):
    def __init__(self):
        super().__init__()
        self.type = ''

    def __str__(self):
        result = super().__str__()     

        return result

class MeleeWeapon(Item):
    def __init__(self):
        super().__init__()
        self.base_damage = 0
        self.max_mod = 0
        self.range = 0
        self.slot = ''
        self.mods = {}
        self.requires = {}

    def __str__(self):
        result = super().__str__()
        result += f'\nDamage: {self.base_damage} - {self.base_damage + self.max_mod}'
        result += f'\nRange: {self.range}'
        result += f'\nSlot: {self.slot}'
        if len(self.mods) != 0:
            result += f'\nModifiers:'
            for key in self.mods:
                result += f'\n  {key}: {self.mods[key]}'
        if len(self.requires) != 0:
            result += f'\nRequirements:'
            for key in self.requires:
                result += f'\n  {key}: {self.requires[key]}'
        return result

class RangedWeapon(MeleeWeapon):
    def __init__(self):
        super().__init__()
        self.ammo_type = ''

    def __str__(self):
        result = super().__str__()
        result += f'\nType of ammo: {self.ammo_type}'
        return result

        
    