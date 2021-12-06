import json
from cursesui.Utility import str_smart_split, pos_neg_int
# from gamelib.Spells import Spell

class Item:
    def get_template_from_type(t):
        if t == 'melee':
            return MeleeWeapon()
        if t == 'ranged':
            return RangedWeapon()
        if t == 'armor':
            return Armor()
        if t == 'ammo':
            return Ammo()
        if t == 'health potion':
            return HealthPotion()
        if t == 'mana potion':
            return ManaPotion()
        if t == 'spell book':
            return SpellBook()
        return Item()

    def get_base_items(names, path):
        data = json.loads(open(path).read())
        result = []
        for item_name in names:
            result += [Item.from_json(data[item_name])]
        return result

    def arr_to_json(items):
        result = []
        for item in items:
            result += [item.json()]
        return result
    
    def separate_items(items):
        normal_items = []
        countable_items = []
        for item in items:
            if isinstance(item, CountableItem):
                countable_items += [item]
            else:
                normal_items += [item]
        return normal_items, countable_items

    def from_json(js):
        t = js['itype']
        result = Item.get_template_from_type(t)
        result.__dict__ = js
        return result

    def __init__(self):
        self.name = ''
        self.itype = 'item'
        self.price = 0
        self.description = ''

    def __str__(self):
        result = f'Name: {self.name}'
        return result

    def get_buy_price(self):
        result = self.price * 4 // 3
        if result == self.price:
            return self.price + 1
        return result # one third more expensive

    def get_sell_price(self):
        return self.price

    def json(self):
        return self.__dict__

    def get_description(self, max_width):
        result = []
        result += [self.name]
        result += ['']
        result += [f'Type: {self.itype}']
        
        desc = str_smart_split(self.description, max_width)
        for d in desc:
            result += [d]
        return result

    def get_cct_display_text(self):
        return self.name

    def copy(self):
        result = Item.get_template_from_type(self.itype)
        result.__dict__ = dict(self.__dict__)
        return result

class GoldPouch(Item):
    def __init__(self):
        super().__init__()

    def get_cct_display_text(self):
        return f'#yellow-black {self.amount} #normal gold'

class EquipableItem(Item):
    def __init__(self):
        super().__init__()
        self.slot = ''
        self.gives_statuses = []
        self.mods = {}

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(3, f'Slot: {self.slot}')
        result.insert(4, '')
        return result

    def get_cct_display_text(self):
        return f'{self.name} (#green-black {self.slot}#normal )'
        
class Armor(EquipableItem):
    def __init__(self):
        super().__init__()
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

    def get_description(self, max_width):
        result = super().get_description(max_width)
        app = 6
        if len(self.requires) != 0:
            result.insert(app - 1, 'Requirements: ')
        else:
            app -= 3
        i = 0
        for i in range(len(self.requires)):
            result.insert(i + app, f'{list(self.requires.keys())[i]}: {list(self.requires.values())[i]}')
        if len(self.requires) != 0:
            result.insert(i + app + 1, '')
        app = i + app + 2
        for i in range(len(self.mods)):
            result.insert(i + app, f'{list(self.mods.keys())[i]}: {pos_neg_int(list(self.mods.values())[i])}')
        if len(self.mods) != 0:
            result.insert(i + app + 1, '')
        return result

class CountableItem(Item):
    def __init__(self):
        super().__init__()
        self.amount = 0

    def get_base_items(d, config_file):
        items = Item.get_base_items(d.keys(), config_file) 
        for i in range(len(items)):
            items[i].amount = list(d.values())[i]
        return items

    def get_cct_display_text(self):
        return f'{self.name} x#magenta-black {self.amount}'

class Ammo(CountableItem):
    def __init__(self):
        super().__init__()
        self.type = ''
        self.damage = 0

    def __str__(self):
        result = super().__str__()     
        result += f'\nType: {self.type}'
        result += f'\nAmount: {self.amount}'
        return result

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(3, '')
        result.insert(4, f'Amount: {self.amount}')
        result.insert(5, '')
        return result

class MeleeWeapon(EquipableItem):
    def __init__(self):
        super().__init__()
        self.base_damage = 0
        self.max_mod = 0
        self.range = 0
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

    def get_description(self, max_width):
        result = super().get_description(max_width)
        app = 6
        result.insert(app - 1, f'Damage: {self.base_damage} - {self.base_damage + self.max_mod}')
        result.insert(app, f'Range: {self.range}')
        result.insert(app + 1, '')
        app += 3
        if len(self.requires) != 0:
            result.insert(app - 1, 'Requirements: ')
        else:
            app -= 3
        i = 0
        for i in range(len(self.requires)):
            result.insert(i + app, f'{list(self.requires.keys())[i]}: {list(self.requires.values())[i]}')
        if len(self.requires) != 0:
            result.insert(i + app + 1, '')
        app = i + app + 2
        for i in range(len(self.mods)):
            result.insert(i + app, f'{list(self.mods.keys())[i]}: {pos_neg_int(list(self.mods.values())[i])}')
        if len(self.mods) != 0:
            result.insert(i + app + 1, '')
        return result

class RangedWeapon(MeleeWeapon):
    def __init__(self):
        super().__init__()
        self.ammo_type = ''

    def __str__(self):
        result = super().__str__()
        result += f'\nType of ammo: {self.ammo_type}'
        return result
    
class UsableItem(CountableItem):
    def __init__(self):
        super().__init__()

    def use(self, entity):
        self.amount -= 1

class HealthPotion(UsableItem):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def use(self, entity):
        super().use(entity)
        entity.add_health(self.restores)
        return [f'{entity.get_cct_name_color()} {entity.name} #normal drinks {self.name} and restores #red-black {self.restores} #normal health']

class ManaPotion(UsableItem):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def use(self, entity):
        super().use(entity)
        entity.add_mana(self.restores)
        return [f'{entity.get_cct_name_color()} {entity.name} #normal drinks {self.name} and restores #cyan-black {self.restores} #normal mana']

class SpellBook(Item):
    def __init__(self):
        super().__init__()
        self.spell_names = []
        self.int_to_learn = 0