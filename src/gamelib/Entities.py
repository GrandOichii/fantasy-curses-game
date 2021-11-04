import json
import gamelib.Items as Items

class Entity:
    def __init__(self):
        self.name = ''
        self.health = 0
        self.max_health = 0
        self.mana = 0
        self.max_mana = 0
        self.STR = 0
        self.DEX = 0
        self.INT = 0
        self.description = ''
        self.items = []
        self.countable_items = []

    def add_health(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
        if self.health < 0:
            self.health = 0

    def add_mana(self, amount):
        self.mana += amount
        if self.mana > self.max_mana:
            self.mana = self.max_mana 
        if self.mana < 0:
            self.mana = 0

class Player(Entity):
    def __init__(self):
        super().__init__()
        self.class_description = ''
        self.class_name = ''

    def add_item(self, item):
        if item == None:
            raise Exception(f'ERR: add_item item is None')
        if isinstance(item, Items.CountableItem):
            for i in self.countable_items:
                if i.name == item.name:
                    i.amount += item.amount
                    return
            self.countable_items += [item]
        else:
            self.items += [item]

    def load_class(self, class_data, assets_path):
        self.max_health = class_data['max_health']
        self.health = self.max_health
        self.max_mana = class_data['max_mana']
        self.mana = self.max_mana
        self.STR = class_data['STR']
        self.DEX = class_data['DEX']
        self.INT = class_data['INT']
        self.class_name = class_data['name']
        self.class_description = class_data['description']
        self.items = Items.Item.get_base_items(class_data['items'], assets_path)
        self.countable_items = Items.CountableItem.get_base_items(class_data['countable_items'], assets_path)
        self.equipment = dict()
        self.equipment['HEAD'] = None
        self.equipment['BODY'] = None
        self.equipment['LEGS'] = None
        self.equipment['ARM1'] = None
        self.equipment['ARM2'] = None

    def meets_requirements(self, requires):
        if 'STR' in requires and requires['STR'] > self.STR:
            return False
        if 'DEX' in requires and requires['DEX'] > self.DEX:
            return False
        if 'INT' in requires and requires['INT'] > self.INT:
            return False
        return True

    def json(self):
        result = dict(self.__dict__)
        result['items'] = Items.Item.arr_to_json(self.items)
        result['countable_items'] = Items.Item.arr_to_json(self.countable_items)
        result['equipment'] = dict()
        slots = ['HEAD', 'BODY', 'LEGS', 'ARM1', 'ARM2']
        for slot in slots:
            result['equipment'][slot] = self.equipment[slot]
        return result

    def from_json(js):
        result = Player()
        result.__dict__ = js
        items = result.items
        result.items = []
        for item in items:
            result.items += [Items.Item.from_json(item)]
        countable_items = result.countable_items
        result.countable_items = []
        for item in countable_items:
            result.countable_items += [Items.Item.from_json(item)]

        return result

        

