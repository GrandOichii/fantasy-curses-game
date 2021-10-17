import json
import gamelib.Items as Items

class Entity:
    def __init__(self):
        self.name = ''
        self.health = 0
        self.mana = 0
        self.STR = 0
        self.DEX = 0
        self.INT = 0
        self.description = ''
        self.items = []
        self.countable_items = []

class Player(Entity):
    def __init__(self):
        super().__init__()
        self.class_description = ''
        self.class_name = ''

    def load_class(self, class_data, assets_path):
        self.health = class_data['health']
        self.mana = class_data['mana']
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

        

