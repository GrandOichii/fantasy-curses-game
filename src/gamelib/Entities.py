import json
import random
from Configuraion import ConfigFile
from gamelib.Items import *
# from gamelib.Spells import *
# import gamelib.Items as Items
import gamelib.Spells as Spells
# from gamelib.Spells import BloodSpell, CombatSpell, Spell

class Entity:
    def __init__(self):
        self.name = ''
        self.health = 0
        self.max_health = 0
        self.mana = 0
        self.max_mana = 0
        self.description = ''
        self.statuses = []

    def get_cct_name_color(self):
        return '#normal'

    def take_damage(self, damage: int):
        armor = self.get_armor() // 2
        actual_damage = damage - armor
        if actual_damage <= 0: actual_damage = 1
        self.health -= actual_damage
        if self.health < 0:
            self.health = 0
        return actual_damage

    def get_armor(self):
        return 0

    def get_max_mana(self):
        return self.max_mana

    def get_max_health(self):
        return self.max_health

    def regenerate_mana(self):
        self.add_mana(1)

    def has_status(self, status: str):
        return False

    def add_statuses(self, statuses: list[str]):
        pass

    def add_health(self, amount: int):
        self.health += amount
        if self.health > self.get_max_health():
            self.health = self.get_max_health()
        if self.health < 0:
            self.health = 0

    def add_mana(self, amount: int):
        self.mana += amount
        if self.mana > self.get_max_mana():
            self.mana = self.get_max_mana() 
        if self.mana < 0:
            self.mana = 0

    def can_cast(self, spell: Spells.Spell):
        if issubclass(type(spell), Spells.BloodSpell):
            return self.health > spell.bloodcost
        return self.mana >= spell.manacost

class Enemy(Entity):
    def __init__(self):
        self.char = '?'
        self.range = 0
        self.damage = 0
        self.damage_mod = 0
        self.armor = 0
        self.description = ''
        self.attack_format = ''
        self.statuses = []
        self.y = 0
        self.x = 0
        # rewards
        self.reward_items = {}
        self.reward_countable_items = {}
        self.min_reward_gold = 0
        self.max_reward_gold = 0

    def get_cct_name_color(self):
        return '#red-black'

    def get_armor(self):
        return self.armor

    def add_statuses(self, statuses: list[str]):
        self.statuses += statuses

    def has_status(self, status: str):
        return status in self.statuses

    def from_enemy_name(name, config_file: ConfigFile):
        enemy_schemas_path = config_file.get('Enemy schemas path')
        result = Enemy()
        data = json.loads(open(enemy_schemas_path, 'r').read())[name]
        result.__dict__ = data
        return result

    def get_rewards(self, config_file: ConfigFile):
        result = {}

        # add gold
        result['gold'] = random.randint(self.min_reward_gold, self.max_reward_gold)

        # add items
        reward_item_names = []
        for item_name in self.reward_items:
            if random.randint(0, 100) <= self.reward_items[item_name]:
                reward_item_names += [item_name]
        result['items'] = Item.get_base_items(reward_item_names, config_file.get('Items path'))

        # add countable items
        reward_countable_items = dict(self.reward_countable_items)
        for item_name in reward_countable_items:
            amount = random.randint(0, reward_countable_items[item_name])
            if amount > 0:
                reward_countable_items[item_name] = amount
        result['countable_items'] = CountableItem.get_base_items(reward_countable_items, config_file.get('Items path'))

        return result

class Player(Entity):
    def __init__(self):
        super().__init__()
        self.class_description = ''
        self.class_name = ''
        self.STR = 0
        self.DEX = 0
        self.INT = 0
        self.gold = 0
        self.items = []
        self.countable_items = []
        self.equipment = dict()
        self.spells = []
        self.temporary_statuses = []

    def get_cct_name_color(self):
        return '#green-black'

    def check_items(self):
        for item in self.countable_items:
            if isinstance(item, UsableItem) and item.amount < 1:
                self.countable_items.remove(item)

    def get_armor(self):
        return self._get_mods_from_equipment('armor')

    def _get_mods_from_equipment(self, mod: str):
        result = 0
        for i in list(self.equipment.values()):
            if i != None:
                item = self.items[i]
                if mod in item.mods:
                    result += item.mods[mod]
        return result

    def get_max_mana(self):
        return self.max_mana + self._get_mods_from_equipment('mana')

    def get_max_health(self):
        return self.max_health + self._get_mods_from_equipment('health')

    def add_rewards(self, rewards: dict):
        self.gold += rewards['gold']
        for item in rewards['items']:
            self.add_item(item)
        for item in rewards['countable_items']:
            self.add_item(item)

    def get_statuses(self):
        result = list(self.temporary_statuses)
        for key in self.equipment:
            item_i = self.equipment[key]
            if item_i != None:
                result += self.items[item_i].gives_statuses
        return result 

    def learn_spells(self, spell_names: list[str], spells_path: str):
        spells = Spells.Spell.get_base_spells(spell_names, spells_path)
        spell_names = [spell.name for spell in self.spells]
        for spell in spells:
            if not spell.name in spell_names:
                self.spells += [spell]

    def add_statuses(self, statuses: list[str]):
        for status in statuses:
            if not status in self.temporary_statuses:
                self.temporary_statuses += [status]

    def get_equipped_items(self):
        result = []
        for key in self.equipment:
            if self.equipment[key] != None:
                result += [self.items[self.equipment[key]]]
        return result

    def has_status(self, status: str):
        for item in self.get_equipped_items():
            if status in item.gives_statuses:
                return True
        if status in self.temporary_statuses:
            return True
        return False

    def add_item(self, item: Item):
        if item == None:
            raise Exception(f'ERR: add_item item is None')
        if isinstance(item, GoldPouch):
            self.gold += item.amount
            return
        if isinstance(item, CountableItem):
            for i in self.countable_items:
                if i.name == item.name:
                    i.amount += item.amount
                    return
            self.countable_items += [item]
        else:
            self.items += [item]

    def remove_item(self, i_id: int):
        for key in self.equipment:
            if self.equipment[key] == i_id:
                self.equipment[key] = None
        self.items.remove(self.items[i_id])

    def load_class(self, class_data: dict, config_file: ConfigFile):
        self.max_health = class_data['max_health']
        self.health = self.max_health
        self.max_mana = class_data['max_mana']
        self.mana = self.max_mana
        self.STR = class_data['STR']
        self.DEX = class_data['DEX']
        self.INT = class_data['INT']
        self.class_name = class_data['name']
        self.class_description = class_data['description']
        self.items = Item.get_base_items(class_data['items'], config_file)
        self.countable_items = CountableItem.get_base_items(class_data['countable_items'], config_file)
        self.equipment = dict()
        self.equipment['HEAD'] = None
        self.equipment['BODY'] = None
        self.equipment['LEGS'] = None
        self.equipment['ARM1'] = None
        self.equipment['ARM2'] = None

    def meets_requirements(self, requires: dict):
        if 'STR' in requires and requires['STR'] > self.STR:
            return False
        if 'DEX' in requires and requires['DEX'] > self.DEX:
            return False
        if 'INT' in requires and requires['INT'] > self.INT:
            return False
        return True

    def get_range(self):
        additional_range = 4
        highest_range = 2 # fist fighting range
        if self.equipment['ARM1'] != None:
            highest_range = max(self.items[self.equipment['ARM1']].range, highest_range)
        if self.equipment['ARM2'] != None:
            highest_range = max(self.items[self.equipment['ARM2']].range, highest_range)
        for spell in self.spells:
            if issubclass(type(spell), Spells.CombatSpell) and spell.range > highest_range:
                highest_range = spell.range
        return highest_range + additional_range
    
    def get_combat_range(self):
        result = 1
        ARM1 = self.equipment['ARM1']
        ARM2 = self.equipment['ARM2']
        if ARM1 != None:
            result = max(self.items[ARM1].range, 0)
        if ARM2 != None:
            result = max(self.items[ARM2].range, 0)
        return result

    def get_ammo_of_type(self, type: str):
        result = []
        for item in self.countable_items:
            if isinstance(item, Ammo) and item.type == type:
                result += [item]
        return result

    def json(self):
        result = dict(self.__dict__)
        # result['items'] = Item.arr_to_json(self.items)
        result['items'] = []
        for item in self.items:
            result['items'] += [item.name]
        result['spells'] = []
        for spell in self.spells:
            result['spells'] += [spell.name]
        # result['countable_items'] = Item.arr_to_json(self.countable_items)
        result['countable_items'] = {}
        for item in self.countable_items:
            result['countable_items'][item.name] = item.amount
        result['equipment'] = dict()
        slots = ['HEAD', 'BODY', 'LEGS', 'ARM1', 'ARM2']
        for slot in slots:
            result['equipment'][slot] = self.equipment[slot]
        return result

    # static methods

    def from_json(js, config_file: ConfigFile):
        result = Player()
        result.__dict__ = js

        items = result.items
        result.items = Item.get_base_items(items, config_file.get('Items path'))
        
        countable_items = result.countable_items
        result.countable_items = CountableItem.get_base_items(countable_items, config_file.get('Items path'))
        
        spells = result.spells
        result.spells = Spells.Spell.get_base_spells(spells, config_file.get('Spells path'))

        return result

        

