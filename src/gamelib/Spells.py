import json

from cursesui.Utility import str_smart_split

import gamelib.Entities as Entities

class Spell:
    def __init__(self):
        self.name = ''
        self.type = ''
        self.description = ''

    def cast(self, user: 'Entities.Entity'):
        return [f'{user.get_cct_name_color()} {user.name} #normal casts #cyan-black {self.name}#normal , but it doesn\'t seem to do anything']

    def json(self):
        return self.__dict__

    def get_description(self, max_width: int):
        result = []
        result += [self.name]
        result += ['']

        desc = str_smart_split(self.description, max_width)
        for d in desc:
            result += [d]
        return result

    def get_cct_display_text(self):
        return self.name

    # static methods

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

    def arr_to_json(spells: list['Spell']):
        result = []
        for spell in spells:
            result += [spell.json()]
        return result

    def get_base_spells(names: list[str], path: str):
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

    def cast(self, user: 'Entities.Entity'):
        user.add_mana(-self.manacost)
        return super().cast(user)

    def get_description(self, max_width: int):
        result = super().get_description(max_width)
        result.insert(2, f'Mana cost: {self.manacost}')
        result.insert(3, '')
        return result

    def get_cct_display_text(self):
        return f'{self.name} (#cyan-black {self.manacost} #normal mana)'

class BloodSpell(NormalSpell):
    def __init__(self):
        super().__init__()
        self.bloodcost = 0

    def cast(self, user: 'Entities.Entity'):
        user.add_health(-self.bloodcost)
        return super().cast(user)

    def get_description(self, max_width: int):
        result = super().get_description(max_width)
        result.insert(2, f'Blood cost: {self.bloodcost}')
        result.insert(3, '')
        return result

    def get_cct_display_text(self):
        return f'{self.name} (#red-black {self.bloodcost} #normal hp)'

class HealSpell(ManaSpell):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def cast(self, user: 'Entities.Entity'):
        super().cast(user)
        user.add_health(self.restores)
        return [f'{user.get_cct_name_color()} {user.name} #normal casts #cyan-black {self.name} #normal and heals #red-black {self.restores} #normal hp']

    def get_description(self, max_width: int):
        result = super().get_description(max_width)
        result.insert(3, f'Heals: {self.restores}')
        return result

class BloodManaSpell(BloodSpell):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def cast(self, user: 'Entities.Entity'):
        super().cast(user)
        user.add_mana(self.restores)
        return [f'{user.get_cct_name_color()} {user.name} #normal casts #red-black {self.name} #normal and restores #cyan-black {self.restores} #normal mana']

    def get_description(self, max_width: int):
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

    def cast(self, user: 'Entities.Entity', enemy: 'Entities.Entity'):
        user.add_mana(-self.manacost)
        user.add_statuses(self.user_statuses)
        enemy.add_statuses(self.enemy_statuses)
        result = [f'{user.get_cct_name_color()} {user.name} #normal casts #cyan-black {self.name}']
        for status in self.user_statuses:
            result += [f'{user.name} has gained status #yellow-black {status}']
        for status in self.enemy_statuses:
            result += [f'{enemy.name} has gained status #yellow-black {status}']
        return result

    def get_description(self, max_width: int):
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

    def get_cct_display_text(self):
        result = f'{self.name} {{}} (#cyan-black {self.manacost} #normal mana)'
        if self.range != -1:
            result = result.format(f'(range: #yellow-black {self.range} #normal )')
            return result
        return result.format('')

class DamageSpell(CombatSpell):
    def __init__(self):
        super().__init__()
        self.damage = 0
    
    def cast(self, user: 'Entities.Entity', enemy: 'Entities.Entity'):
        result = super().cast(user, enemy)
        enemy.add_health(-self.damage)
        result += [f'{user.get_cct_name_color()} {self.name} #normal deals #red-black {self.damage} #normal to {enemy.get_cct_name_color()} {enemy.name}']
        return result

    def get_description(self, max_width: int):
        result = super().get_description(max_width)
        result.insert(4, f'Damage: {self.damage}')
        return result

    