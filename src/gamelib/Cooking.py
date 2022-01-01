import curses
import json
import collections

import gamelib.Entities as Entities

from Configuraion import ConfigFile
from ncursesui.Elements import Window
from ncursesui.Utility import draw_borders, message_box, put
from gamelib.Items import CountableItem, Item

compare_lists = lambda x, y: collections.Counter(x) == collections.Counter(y)

class Recipe:
    def from_json(js):
        recipe = Recipe(None, None)
        recipe.__dict__ = js
        return recipe

    def get_result(pot: list[tuple[str, int]], recipes: list['Recipe']):
        if len(pot) == 0:
            return None
        for recipe in recipes:
            if recipe.matches_pot(pot):
                return recipe.result
        return 'Dubious food'

    def __init__(self, ingredients: list[str], result: str):
        self.ingredients = ingredients
        self.result = result

    def matches_pot(self, pot: list[tuple[str, int]]):
        item_names = [item[0] for item in pot]
        return compare_lists(self.ingredients, item_names)
        # for ingredient in self.ingredients:
        #     if not ingredient in item_names:
        #         return False
        # for ingredient in item_names:

        # return True

class Cooking:
    def __init__(self, player: Entities.Player, config_file: ConfigFile):
        self.player = player
        self.ingredients = player.get_ingredients()
        self.amounts = []
        for _ in self.ingredients:
            self.amounts += [0]

        self.item_choice = 0
        self.log_messages = []
        self.recipes = []
        self.cooked_item_names = []
        self.add_recipes(config_file.get('Recipes path'))

        self.items_path = config_file.get('Items path')

    def add_recipes(self, path: str):
        raw_recipes = json.loads(open(path, 'r').read())
        for recipe in raw_recipes:
            self.recipes += [Recipe.from_json(recipe)]

    def get_ingredients(self):
        result = []
        for i in range(len(self.amounts)):
            item = self.ingredients[i].copy()
            item.amount -= self.amounts[i]
            result += [item]
        return result

    def get_pot(self):
        result = []
        for i in range(len(self.amounts)):
            if self.amounts[i] != 0:
                result += [(self.ingredients[i].name, self.amounts[i])]
        return result

    def reduce_amounts(self):
        for i in range(len(self.amounts)):
            self.ingredients[i].amount -= self.amounts[i]

    def reset_amounts(self):
        for i in range(len(self.amounts)):
            self.amounts[i] = 0

    def cook(self):
        pot = self.get_pot()
        if len(pot) == 0:
            return
        cooked_item_name = Recipe.get_result(pot, self.recipes)
        self.cooked_item_names += [cooked_item_name]
        self.log_messages += [f'#green-black {self.player.name} #normal cooked #cyan-black {cooked_item_name}#normal !']
        self.reduce_amounts()
        self.reset_amounts()
        return cooked_item_name

    def add_selected_item_to_pot(self):
        # selected_item = self.ingredients[self.item_choice].copy()
        # selected_item.amount -= self.amounts[self.item_choice]
        # if selected_item.amount > 0:
            # self.amounts[self.item_choice] += 1
        if self.amounts[self.item_choice] == 0 and self.ingredients[self.item_choice].amount != 0:
            self.amounts[self.item_choice] = 1

    def move_down(self):
        self.item_choice += 1
        if self.item_choice >= len(self.amounts):
            self.item_choice = 0

    def move_up(self):
        self.item_choice -= 1
        if self.item_choice < 0:
            self.item_choice = len(self.amounts) - 1

    def add_cooked_items(self):
        items = Item.get_base_items(self.cooked_item_names, self.items_path)
        for item in items:
            item.amount = 1
            self.player.add_item(item)

class CursesCooking:
    def __init__(self, parent: Window, player: Entities.Player, config_file: ConfigFile):
        self.parent = parent
        self.cooking = Cooking(player, config_file)

    def start(self):
        piw_height = self.parent.HEIGHT * 3 // 4
        piw_width = self.parent.WIDTH
        self.player_ingredients_window = curses.newwin(piw_height, piw_width, 0, 0)
        self.player_ingredients_window.keypad(1)
        
        pw_height = self.parent.HEIGHT - piw_height
        pw_width = piw_width
        self.pot_window = curses.newwin(pw_height, pw_width, piw_height, 0)
        self.pot_window.keypad(1)
        self.main_loop()

    def get_key(self):
        return self.player_ingredients_window.getch()

    def main_loop(self):
        while True:
            self.draw()
            key = self.get_key()
            if key == 10: # ENTER
                self.cook()
            if key == 32: # SPACE
                self.add_to_pot()
            if key == curses.KEY_UP:
                self.cooking.move_up()
            if key == curses.KEY_DOWN:
                self.cooking.move_down()
            if key == 120: # x
                self.reset_amounts()
            if key == 27: # ESC
                if message_box(self.parent, 'Finish cooking?', ['No', 'Yes']) == 'Yes':
                    break

        # add cooked items
        self.cooking.add_cooked_items()

        self.player_ingredients_window.clear()
        self.pot_window.clear()
        self.player_ingredients_window.refresh()
        self.pot_window.refresh()

    def reset_amounts(self):
        self.cooking.reset_amounts()

    def add_to_pot(self):
        self.cooking.add_selected_item_to_pot()

    def cook(self):
        if len(self.cooking.get_pot()) == 0:
            return
        if message_box(self.parent, 'Cook?', ['Yes', 'No']) == 'Yes':
            cooked_item_name = self.cooking.cook()
            message_box(self.parent, f'You made #cyan-black {cooked_item_name}', ['Ok'])

    def get_log_messages(self):
        return self.cooking.log_messages

    # drawers

    def draw(self):
        self.draw_player_ingredients_window()
        self.draw_pot_window()

        self.player_ingredients_window.refresh()
        self.pot_window.refresh()

    def draw_player_ingredients_window(self):
        self.player_ingredients_window.clear()
        draw_borders(self.player_ingredients_window)
        put(self.player_ingredients_window, 0, 1, '#magenta-black Ingredients')
        items = self.cooking.get_ingredients()
        for i in range(len(items)):
            attr = curses.A_REVERSE if i == self.cooking.item_choice else 0
            put(self.player_ingredients_window, 1 + i, 2, f'{items[i].name} #magenta-black x{items[i].amount}', attr)

    def draw_pot_window(self):
        self.pot_window.clear()
        draw_borders(self.pot_window)
        put(self.pot_window, 0, 1, '#magenta-black Pot')
        pot = self.cooking.get_pot()
        for i in range(len(pot)):
            put(self.pot_window, 1 + i, 2, f'{pot[i][0]} #magenta-black x{pot[i][1]}')
        