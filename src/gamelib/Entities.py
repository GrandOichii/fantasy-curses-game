import json
import gamelib.Items

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

class Player(Entity):
    def __init__(self):
        super().__init__()
        self.class_description = ''

    def load_class(self, class_data, assets_path):
        self.health = class_data['health']
        self.mana = class_data['mana']
        self.STR = class_data['STR']
        self.DEX = class_data['DEX']
        self.INT = class_data['INT']
        self.class_description = class_data['description']
        self.items = gamelib.Items.Item.get_base_items(class_data['items'], assets_path)

    def json(self):
        result = dict(self.__dict__)
        result['items'] = gamelib.Items.Item.arr_to_json(self.items)
        return result
        

