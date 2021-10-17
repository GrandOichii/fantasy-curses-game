import json

class Item:
    def get_base_items(names, path):
        data = json.loads(open(path).read())
        result = []
        for type in data:
            for item in data[type]:
                if item['name'] in names:
                    result += [Item.from_json(item)]
        return result

    def arr_to_json(items):
        result = []
        for item in items:
            result += [item.json()]
        return result
    
    def from_json(js):
        result = Item()
        t = js['itype']
        if t == 'melee':
            result = MeleeWeapon()
        if t == 'ranged':
            result = RangedWeapon()
        if t == 'armor':
            result = Armor()
        if t == 'ammo':
            result = Ammo()

        result.__dict__ = js
        return result

    def __init__(self):
        self.name = ''
        self.itype = 'item'

    def __str__(self):
        result = f'Name: {self.name}'
        return result

    def json(self):
        return self.__dict__

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

class CountableItem(Item):
    def __init__(self):
        super().__init__()
        self.amount = 0

    def get_base_items(d, path):
        items = Item.get_base_items(d.keys(), path)
        result = []
        for i in range(len(items)):
            items[i].amount = list(d.values())[i]
        return items

class Ammo(CountableItem):
    def __init__(self):
        super().__init__()
        self.type = ''

    def __str__(self):
        result = super().__str__()     
        result += f'\nType: {self.type}'
        result += f'\nAmount: {self.amount}'
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

        
    