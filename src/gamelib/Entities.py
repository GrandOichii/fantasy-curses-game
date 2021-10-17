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

    def json(self):
        result = dict(self.__dict__)
        result['items'] = Items.Item.arr_to_json(self.items)
        result['countable_items'] = Items.Item.arr_to_json(self.countable_items)
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

        

