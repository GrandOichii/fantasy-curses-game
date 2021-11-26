import json

from Utility import str_smart_split

class Spell:
    def __init__(self):
        self.name = ''
        self.type = ''
        self.description = ''

    def cast(self, user):
        return [f'{user.name} casts {self.name}, but it doesn\'t seem to do anything']

    def json(self):
        return self.__dict__

    def get_description(self, max_width):
        result = []
        result += [self.name]
        result += ['']

        desc = str_smart_split(self.description, max_width)
        for d in desc:
            result += [d]
        return result

    def from_json(js):
        result = Spell()
        t = js['type']
        if t == 'heal_spell':
            result = HealSpell()
        if t == 'blood_spell_mana':
            result = BloodManaSpell()
        if t == 'damage_spell':
            result = DamageSpell()
        if t == 'combat_spell':
            result = CombatSpell()
        result.__dict__ = js
        return result

    def arr_to_json(spells):
        result = []
        for spell in spells:
            result += [spell.json()]
        return result

    def get_base_spells(names, path):
        data = json.loads(open(path, 'r').read())
        result = []
        for item_name in names:
            result += [Spell.from_json(data[item_name])]
        return result

class NormalSpell(Spell):
    def __init__(self):
        super().__init__()

class ManaSpell(NormalSpell):
    def __init__(self):
        super().__init__()
        self.manacost = 0

    def cast(self, user):
        user.add_mana(-self.manacost)
        return super().cast(user)

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(2, f'Mana cost: {self.manacost}')
        result.insert(3, '')
        return result

class BloodSpell(NormalSpell):
    def __init__(self):
        super().__init__()
        self.bloodcost = 0

    def cast(self, user):
        user.add_health(-self.bloodcost)
        return super().cast(user)

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(2, f'Blood cost: {self.bloodcost}')
        result.insert(3, '')
        return result

class HealSpell(ManaSpell):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def cast(self, user):
        super().cast(user)
        user.add_health(self.restores)
        return [f'{user.name} casts {self.name} and heals {self.restores} hp']

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(3, f'Heals: {self.restores}')
        return result

class BloodManaSpell(BloodSpell):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def cast(self, user):
        super().cast(user)
        user.add_mana(self.restores)
        return [f'{user.name} casts {self.name} and restores {self.restores} mana']

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(3, f'Restores mana: {self.restores}')
        return result

class CombatSpell(Spell):
    def __init__(self):
        super().__init__()
        self.user_statuses = []
        self.enemy_statuses = []
        self.manacost = 0
        self.range = 0

    def cast(self, user, enemy):
        user.add_mana(-self.manacost)
        user.add_statuses(self.user_statuses)
        enemy.add_statuses(self.enemy_statuses)
        result = [f'{user.name} casts {self.name}']
        for status in self.user_statuses:
            result += [f'{user.name} has gained status {status}']
        for status in self.enemy_statuses:
            result += [f'{enemy.name} has gained status {status}']
        return result

    def get_description(self, max_width):
        result = super().get_description(max_width)
        pos = 2
        result.insert(pos, f'Mana cost: {self.manacost}')
        pos += 1
        if self.range != -1:
            result.insert(pos, f'Range: {self.range}')
            pos += 1
        if len(self.user_statuses) != 0:
            us = f'User statuses: {self.user_statuses[0]}'
            for i in range(1, len(self.user_statuses)):
                us += f', {self.user_statuses[i]}'
            result.insert(pos, us)
            pos += 1
        if len(self.enemy_statuses) != 0:
            es = f'Enemy statuses: {self.enemy_statuses[0]}'
            for i in range(1, len(self.enemy_statuses)):
                es += f', {self.enemy_statuses[i]}'
            result.insert(pos, es)
            pos += 1
        result.insert(pos, '')
        return result

class DamageSpell(CombatSpell):
    def __init__(self):
        super().__init__()
        self.damage = 0
    
    def cast(self, user, enemy):
        result = super().cast(user, enemy)
        enemy.add_health(-self.damage)
        result += [f'{self.name} deals {self.damage} to {enemy.name}']
        return result

    def get_description(self, max_width):
        result = super().get_description(max_width)
        result.insert(4, f'Damage: {self.damage}')
        return result

    