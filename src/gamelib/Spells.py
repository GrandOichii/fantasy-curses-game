import json


class Spell:
    def __init__(self):
        self.name = ''
        self.type = ''

    def cast(self, user):
        return [f'{user.name} casts {self.name}, but it doesn\'t seem to do anything']

    def json(self):
        return self.__dict__

    def from_js(js):
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

    def get_base_spells(names, spells_path):
        data = json.loads(open(spells_path, 'r').read())
        result = []
        for type in data:
            for spell in data[type]:
                if spell['name'] in names:
                    result += [Spell.from_js(spell)]
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

class BloodSpell(NormalSpell):
    def __init__(self):
        super().__init__()
        self.bloodcost = 0

    def cast(self, user):
        user.add_health(-self.bloodcost)
        return super().cast(user)

class HealSpell(ManaSpell):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def cast(self, user):
        super().cast(user)
        user.add_health(self.restores)
        return [f'{user.name} casts {self.name} and heals {self.restores} hp']

class BloodManaSpell(BloodSpell):
    def __init__(self):
        super().__init__()
        self.restores = 0

    def cast(self, user):
        super().cast(user)
        user.add_mana(self.restores)
        return [f'{user.name} casts {self.name} and restores {self.restores} mana']

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

class DamageSpell(CombatSpell):
    def __init__(self):
        super().__init__()
        self.damage = 0
    
    def cast(self, user, enemy):
        result = super().cast(user, enemy)
        enemy.add_health(-self.damage)
        result += [f'{self.name} deals {self.damage} to {enemy.name}']
        return result

    