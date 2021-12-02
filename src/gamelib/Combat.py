import curses
import random
from curses import textpad
from curses.textpad import rectangle

import gamelib.Items as Items

from gamelib.Entities import Player, Enemy
from gamelib.Items import MeleeWeapon, RangedWeapon
from gamelib.Spells import BloodSpell, CombatSpell, NormalSpell
from cursesui.Utility import cct_len, put, draw_borders, drop_down_box, calc_pretty_bars, str_smart_split, SINGLE_ELEMENT, MULTIPLE_ELEMENTS

class Action:
    def __init__(self, parent, char, caption, picture, user, other):
        self.parent = parent
        self.char = char
        self.caption = caption
        self.user = user
        self.other = other
        self.picture = picture

    def run(self):
        pass

    def get_as_option(self):
        return f'({self.char}) {self.caption}'

class WaitAction(Action):
    def __init__(self, parent, char, user):
        super().__init__(parent, char, 'Wait', '..', user, None)

    def run(self):
        return [f'{self.user.name} waits.']      

class MoveAction(Action):
    def __init__(self, parent, char, caption, user, other, move_val):
        a = abs(move_val)
        lines = '-' if a == 1 else '='
        picture = f'{lines}>' if move_val > 0 else f'<{lines}'
        if move_val == -3:
            picture = f'{chr(171)}='
        if move_val == 3:
            picture = f'={chr(187)}'
        super().__init__(parent, char, caption, picture, user, other)
        self.move_val = move_val

    def run(self):
        self.parent.distance -= self.move_val
        if self.parent.distance < 1:
            self.parent.distance = 1
        action = 'ERR'
        if self.move_val == -3:
            action = 'sprints away from'
        if self.move_val == -2:
            action = 'runs away from'
        if self.move_val == -1:
            action = 'walks away from'
        if self.move_val == 1:
            action = 'walks toward to'
        if self.move_val == 2:
            action = 'runs toward to'
        if self.move_val == 3:
            action = 'sprints toward to'
        result = [f'{self.user.name} {action} {self.other.name}.']
        return result

class AttackWithoutWeaponEnemyAction(Action):
    def __init__(self, parent, char, caption, user, other):
        super().__init__(parent, char, caption, 'XX', user, other)

    def run(self):
        damage = self.user.STR // 5
        self.other.add_health(-damage)
        return [f'{self.user.name} punches {self.other.name} and deals {damage} damage.']

class AttackMeleeEnemyAction(Action):
    def __init__(self, parent, char, caption, user, other, weapon):
        super().__init__(parent, char, caption, 'XX', user, other)
        self.weapon = weapon

    def run(self):
        damage = self.weapon.base_damage
        damage += random.randint(0, self.weapon.max_mod)
        self.other.add_health(-damage)
        return [f'{self.user.name} attacks with {self.weapon.name} and hits {self.other.name} for {damage} damage.']

class AttackRangedEnemyAction(Action):
    def __init__(self, parent, char, caption, user, other, weapon, ammo):
        super().__init__(parent, char, caption, 'XX', user, other)
        self.weapon = weapon
        self.ammo = ammo

    def run(self):
        damage = self.weapon.base_damage
        damage += self.ammo.damage
        damage += random.randint(0, self.weapon.max_mod)
        self.ammo.amount -= 1
        self.other.add_health(-damage)
        return [f'{self.user.name} attacks with {self.weapon.name} and hits {self.other.name} for {damage} damage.']

class AttackPlayerAction(Action):
    def __init__(self, parent, user, other):
        super().__init__(parent, '?', '-', 'XX', user, other)

    def run(self):
        damage = self.user.damage
        damage += random.randint(0, self.user.damage_mod)
        self.other.add_health(-damage)
        curses.flash()
        return [f'{self.user.name} attacks and deals {damage} damage to {self.other.name}.']

class UseItemAction(Action):
    def __init__(self, parent, char, caption, user, item):
        super().__init__(parent, char, caption, '-I', user, None)
        self.item = item

    def run(self):
        return self.item.use(self.user)

class CastSpellAction(Action):
    def __init__(self, parent, char, caption, user, other, spell):
        super().__init__(parent, char, caption, 'AV', user, other)
        self.spell = spell

    def run(self):
        if issubclass(type(self.spell), CombatSpell):
            return self.spell.cast(self.user, self.other)
        if issubclass(type(self.spell), NormalSpell):
            return self.spell.cast(self.user)
        raise Exception(f'ERR: can\'t cast spell {self.spell.name}')

class CombatEncounter:
    def __init__(self, attacker, defender, distance, height, width, config_file):
        self.config_file = config_file
        
        self.chars = ['s', 'd', 'f', 'g', 'h', 'j', 'k', 'l']
        self.HEIGHT = height
        self.WIDTH = width

        self.calc_height_width()

        self.window = None

        self.entities = [attacker, defender]
        self.turn_id = 0
        self.combat_log = []
        self.cl_page = 0
        self.add_to_combat_log(f'{attacker.name} attacks {defender.name}!')
        self.distance = int(distance)

        self.action_id = 0

        self.player_actions = []

        self.last_player_picture = None
        self.last_enemy_picture = None

        self.player_id = -1
        for i in range(len(self.entities)):
            if isinstance(self.entities[i], Player):
                self.player_id = i
        if self.player_id == -1:
            raise Exception('ERR: in encounter to player was found')

    def calc_height_width(self):
        self.box_height = self.HEIGHT - 2
        self.box_width = self.WIDTH // 3

        self.action_box_height = 3
        self.action_box_width = 4
        
        self.middle_height = self.HEIGHT - 2
        self.middle_width = self.WIDTH - self.box_width * 2 - 1

        self.combat_log_window_height = self.HEIGHT * 3 // 8
        self.combat_log_window_width = self.middle_width
        self.combat_log_message_width = self.combat_log_window_width - 3

        self.cl_limit = self.combat_log_window_height - 2

    def draw_borders(self, w):
        w.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def update_player_options(self):
        self.player_actions = []
        player = self.get_player()
        enemy = self.get_enemy()
        char_i = 0
        if player.get_combat_range() >= self.distance:
            self.player_actions += [Action(self, 'a', 'Attack', 'XX', player, enemy)]
        if len(player.spells) > 0:
            self.player_actions += [Action(self, 'c', 'Cast Spell', 'VA', player, enemy)]
        char_i = 2
        self.player_actions += [MoveAction(self, self.chars[char_i], 'Flee', player, enemy, -2)]
        char_i += 1
        self.player_actions += [MoveAction(self, self.chars[char_i], 'Walk away', player, enemy, -1)]
        char_i += 1
        if self.distance > 1:
            self.player_actions += [MoveAction(self, self.chars[char_i], 'Walk towards', player, enemy, 1)]
            char_i += 1
        if self.distance > 2:
            self.player_actions += [MoveAction(self, self.chars[char_i], 'Charge', player, enemy, 2)]
            char_i += 1
        if player.has_status('fast'):
            self.player_actions += [MoveAction(self, self.chars[char_i], 'Sprint away', player, enemy, -3)]
            char_i += 1
            if self.distance > 3:
                self.player_actions += [MoveAction(self, self.chars[char_i], 'Sprint toward', player, enemy, 3)]
                char_i += 1
        if len(self.get_usable_item_display_names()) != 0:
            self.player_actions += [Action(self, 'u', 'Use Item', '??', player, enemy)]
        # at the very end
        self.player_actions += [WaitAction(self, 'w', player)]

    def draw_player_actions(self):
        max_options = 10
        for i in range(max_options):
            self.player_actions_window.addstr(1 + i, 1, ' ' * (self.box_width - 2))
        for i in range(len(self.player_actions)):
            if i == self.action_id:
                self.player_actions_window.addstr(1 + i, 1, self.player_actions[i].get_as_option(), curses.A_REVERSE)
            else:
                self.player_actions_window.addstr(1 + i, 1, self.player_actions[i].get_as_option())

    def draw_enemy_info(self):
        enemy = self.get_enemy()
        y_first = self.action_box_height + 1
        y_last = self.box_height - 2
        # clear screen
        for i in range(y_first, y_last + 1):
            self.enemy_window.addstr(i, 1, ' ' * (self.box_width - 3))
        
        # display health
        put(self.enemy_window, y_first, 1, f'Health: #red-black {calc_pretty_bars(enemy.health, enemy.max_health, self.box_width - 16)}')
        self.enemy_window.addstr(y_first, self.box_width - 6, f'(  )')
        put(self.enemy_window, y_first, self.box_width - 5, f'#red-black {enemy.health}')
        # display mana
        put(self.enemy_window, y_first + 1, 1, f'  Mana: #cyan-black {calc_pretty_bars(enemy.mana, enemy.max_mana, self.box_width - 16)}')
        self.enemy_window.addstr(y_first + 1, self.box_width - 6, f'(  )')
        put(self.enemy_window, y_first + 1, self.box_width - 5, f'#cyan-black {enemy.mana}')

        # display statuses
        self.enemy_window.addstr(y_first + 2, 1, 'Statuses:')
        for i in range(len(enemy.statuses)):
            self.enemy_window.addstr(y_first + 3 + i, 2, enemy.statuses[i])

        y_first = y_first + 5 + i
              # display distance
        self.enemy_window.addstr(y_first, 1, f'DISTANCE: {self.distance}')

    def draw_player_info(self):
        player = self.get_player()
        y_first = self.action_box_height + 1
        y_last = self.box_height - 2
        statuses = player.get_statuses()
        # clear screen
        for i in range(y_first, y_last + 1):
            self.player_window.addstr(i, 1, ' ' * (self.box_width - 3))

        # display health
        put(self.player_window, y_first, 1, f'Health: #red-black {calc_pretty_bars(player.health, player.max_health, self.box_width - 15)}')
        self.player_window.addstr(y_first, self.box_width - 5, f'(  )')
        put(self.player_window, y_first, self.box_width - 4, f'#red-black {player.health}')
        # display mana
        put(self.player_window, y_first + 1, 1, f'  Mana: #cyan-black {calc_pretty_bars(player.mana, player.max_mana, self.box_width - 15)}')
        self.player_window.addstr(y_first + 1, self.box_width - 5, f'(  )')
        put(self.player_window, y_first + 1, self.box_width - 4, f'#cyan-black {player.mana}')

        # display statuses
        self.player_window.addstr(y_first + 2, 1, 'Statuses:')
        for i in range(len(statuses)):
            self.player_window.addstr(y_first + 3 + i, 2, statuses[i])

    def draw_option_boxes(self):
        rectangle(self.player_window, 1, 1, self.action_box_height, self.action_box_width)
        rectangle(self.enemy_window, 1, 1, self.action_box_height, self.action_box_width)
        self.draw_last_pictures()

    def draw_last_pictures(self):
        if self.last_player_picture != None:
            self.player_window.addstr(2, 2, self.last_player_picture)
        if self.last_enemy_picture != None:
            self.enemy_window.addstr(2, 2, self.last_enemy_picture)
        
    def draw(self):
        # display distance
        self.draw_combat_log()
        self.draw_player_actions()
        self.draw_last_pictures()

        # displaying info
        self.draw_player_info()
        self.draw_enemy_info()

        draw_borders(self.window)
        draw_borders(self.player_window)
        self.player_window.addstr(0, 1, self.get_player().name)
        self.draw_option_boxes()
        draw_borders(self.enemy_window)
        self.enemy_window.addstr(0, 1, self.get_enemy().name)
        draw_borders(self.player_actions_window)
        self.player_actions_window.addstr(0, 1, 'Player options')

        self.window.refresh()
        self.player_window.refresh()
        self.enemy_window.refresh()
        self.player_actions_window.refresh()
        self.combat_log_window.refresh()

    def draw_combat_log(self):
        self.combat_log_window.clear()
        draw_borders(self.combat_log_window)
        self.combat_log_window.addstr(0, 1, 'Combat log')
        y = 0
        first = 0
        last = len(self.combat_log) - 1
        if len(self.combat_log) > self.cl_limit:
            first = self.cl_page
            last = self.cl_page + self.cl_limit - 1
        for i in range(first, last + 1):
            put(self.combat_log_window, 1 + y, 1, self.combat_log[i])
            y += 1
        if len(self.combat_log) > self.cl_limit:
            if self.cl_page != 0:
                self.combat_log_window.addch(1, self.combat_log_window_width - 1, curses.ACS_UARROW)
            if self.cl_page !=  len(self.combat_log) - self.cl_limit:
                self.combat_log_window.addch(self.combat_log_window_height - 2, self.combat_log_window_width - 1, curses.ACS_DARROW)

    def start(self):
        self.window = curses.newwin(self.HEIGHT, self.WIDTH, 0, 0)
        self.window.keypad(1)
        self.player_actions_window = curses.newwin(self.middle_height - self.combat_log_window_height, self.middle_width, 1, self.box_width + 1)
        self.combat_log_window = curses.newwin(self.combat_log_window_height, self.combat_log_window_width, self.HEIGHT - self.combat_log_window_height - 1, self.box_width + 1)
        self.player_window = curses.newwin(self.box_height, self.box_width, 1, 1)
        self.enemy_window = curses.newwin(self.box_height, self.box_width - 1, 1, self.WIDTH - self.box_width)
        self.update_player_options()
        self.draw()
        self.main_loop()
       
    def main_loop(self):
        self.player_cast_spell = False
        self.enemy_cast_spell = False
        while True:
            key = self.window.getch()
            
            # ONLY FOR DEBUG
            if key == 81: # Q
                break
            if key == 32: # SPACE
                self.add_to_combat_log('Lorem ipsum ibsolares she will never miss me')

            if key == 60: # <
                if len(self.combat_log) > self.cl_limit:
                    self.cl_page -= 1
                    if self.cl_page < 0:
                        self.cl_page = 0
                    self.draw_combat_log()
                    self.combat_log_window.refresh()
                    continue
            if key == 62: # >
                if len(self.combat_log) > self.cl_limit:
                    self.cl_page += 1
                    if self.cl_page > len(self.combat_log) - self.cl_limit:
                        self.cl_page = len(self.combat_log) - self.cl_limit
                    self.draw_combat_log()
                    self.combat_log_window.refresh()
                    continue
            if key == 259: # UP
                self.action_id -= 1
                if self.action_id < 0:
                    self.action_id = len(self.player_actions) - 1
            if key == 258: # DOWN
                self.action_id += 1
                if self.action_id >= len(self.player_actions):
                    self.action_id = 0
            if key == 10: # ENTER
                # execute player action
                action = self.player_actions[self.action_id]
                if action.caption == 'Attack':
                    action = self.get_player_attack_action()
                elif action.caption == 'Use Item':
                    action = self.choose_player_item()
                elif action.caption == 'Cast Spell':
                    action = self.choose_player_spell()
                if action != None:
                    if not self.player_cast_spell:
                        self.get_player().regenerate_mana()
                    if not self.enemy_cast_spell:
                        self.get_enemy().regenerate_mana()
                    self.player_cast_spell = False
                    self.enemy_cast_spell = False
                    self.last_player_picture = action.picture
                    responses = action.run()
                    for r in responses:
                        self.add_to_combat_log(r)
                    self.action_id = 0
                    # execute enemy action
                    action = self.get_enemy_action()
                    self.last_enemy_picture = action.picture
                    responses = action.run()
                    for r in responses:
                        self.add_to_combat_log(r)
                    # last
                    self.update_player_options()
            index = self.index_by_key(key)
            if index != -1:
                self.action_id = index
            if self.get_player().health == 0:
                self.player_lost()
                break
            if self.get_enemy().health == 0:
                self.player_won()
                break
            
            self.draw()

    def add_to_combat_log(self, message):
        message = '- ' + message
        self.combat_log += str_smart_split(message, self.combat_log_message_width)
        if len(self.combat_log) > self.cl_limit:
            self.cl_page = len(self.combat_log) - self.cl_limit

    def get_player(self):
        return self.entities[self.player_id]

    def get_enemy(self):
        return self.entities[1 - self.player_id]

    def get_player_attack_action(self):
        player = self.get_player()
        enemy = self.get_enemy()
        ARM1_i = player.equipment['ARM1']
        ARM2_i = player.equipment['ARM2']
        has_arm1 = ARM1_i != None
        has_arm2 = ARM2_i != None
        if not has_arm1 and not has_arm2:
            return AttackWithoutWeaponEnemyAction(self, 'a', '-', player, enemy)
        weapon = None
        w_width = 0
        weapons = []
        if has_arm1 and has_arm2 and ARM1_i == ARM2_i:
            weapon = player.items[ARM1_i]
            weapons += [weapon]
        else:
            # player has two weapons
            if has_arm1:
                weapons += [player.items[ARM1_i]]
            if has_arm2:
                weapons += [player.items[ARM2_i]]
        display_names = [f'{w.name} (range: {w.range})' for w in weapons]
        w_height = len(display_names) + 2
        w_width = max([len(d) for d in display_names]) + 2
        w_choice_window = curses.newwin(w_height, w_width, 2, 12 + self.box_width)
        w_choice_window.keypad(1)
        draw_borders(w_choice_window)
        choice_i = 0
        key = -1
        while True:
            for i in range(w_height - 2):
                w_choice_window.addstr(1 + i, 1, ' ' * (w_width - 2))
            if key == 259: # UP
                choice_i -= 1
                if choice_i < 0:
                    choice_i = len(display_names) - 1
            if key == 258: # DOWN
                choice_i += 1
                if choice_i >= len(display_names):
                    choice_i = 0
            if key == 10: # ENTER
                break
            if key == 27: # ESC
                return None
            for i in range(len(display_names)):
                if i == choice_i:
                    w_choice_window.addstr(1 + i, 1, display_names[i], curses.A_REVERSE)
                else:
                    w_choice_window.addstr(1 + i, 1, display_names[i])
            key = w_choice_window.getch()
        weapon = weapons[choice_i]
        if weapon.range < self.distance:
            return None
        # we have the weapon
        if isinstance(weapon, MeleeWeapon) and not isinstance(weapon, RangedWeapon):
            return AttackMeleeEnemyAction(self, 'a', '-', player, enemy, weapon)
        # this is a ranged weapon
        ammo_items = player.get_ammo_of_type(weapon.ammo_type)
        if len(ammo_items) == 0: # BAD
            return None
        display_names = [item.get_cct_display_text() for item in ammo_items]
        a_w_height = len(ammo_items) + 2
        a_w_width = max([len(d) for d in display_names]) + 2
        a_window = curses.newwin(a_w_height, a_w_width, 5, 12 + w_width)
        a_window.keypad(1)
        draw_borders(a_window)
        choice_i = 0
        for i in range(len(display_names)):
            if i == choice_i:
                a_window.addstr(1 + i, 1, display_names[i], curses.A_REVERSE)
            else:
                a_window.addstr(1 + i, 1, display_names[i])
        while True:
            key = a_window.getch()
            if key == 259: # UP
                choice_i -= 1
                if choice_i < 0:
                    choice_i = len(display_names) - 1
            if key == 258: # DOWN
                choice_i += 1
                if choice_i >= len(display_names):
                    choice_i = 0
            if key == 10: # ENTER
                break
            if key == 27: # ESC
                return
            for i in range(len(display_names)):
                if i == choice_i:
                    a_window.addstr(1 + i, 1, display_names[i], curses.A_REVERSE)
                else:
                    a_window.addstr(1 + i, 1, display_names[i])
        ammo = ammo_items[choice_i]
        return AttackRangedEnemyAction(self, 'a', '-', player, enemy, weapon, ammo)

    def get_usable_item_display_names(self):
        result = []
        for item in self.get_player().countable_items:
            if isinstance(item, Items.UsableItem):
                result += [item.get_cct_display_text()]
        return result

    def get_usable_items(self):
        result = []
        for item in self.get_player().countable_items:
            if isinstance(item, Items.UsableItem):
                result += [item]
        return result

    def choose_player_item(self):
        max_items = 4
        item_names = self.get_usable_item_display_names()
        if len(item_names) == 0:
            return None
        results = drop_down_box(item_names, max_items, self.action_id + 2, 14 + self.box_width, SINGLE_ELEMENT)
        if len(results) == 0:
            return None
        result_id = results[0]
        return UseItemAction(self, 'u', '-', self.get_player(), self.get_usable_items()[result_id])
    
    def get_usable_spells(self):
        player = self.get_player()
        result = []
        for spell in player.spells:
            if not player.can_cast(spell):
                continue
            if issubclass(type(spell), CombatSpell) and spell.range != -1 and spell.range < self.distance:
                continue
            result += [spell]
        return result

    def get_usable_spell_display_names(self, spells):
        result = []
        for spell in spells:
            # cost = 0
            # cost_type = 'mana'
            # if issubclass(type(spell), BloodSpell):
            #     cost = spell.bloodcost
            #     cost_type = 'hp'
            # else:
            #     cost = spell.manacost
            # if issubclass(type(spell), CombatSpell) and spell.range != -1:
            #     result += [f'{spell.name} (range: {spell.range}) ({cost} {cost_type})']
            # else:
            #     result += [f'{spell.name} ({cost} {cost_type})']
            result += [spell.get_cct_display_text()]
        return result
    
    def choose_player_spell(self):
        max_spells = 4
        spells = self.get_usable_spells()
        spell_names = self.get_usable_spell_display_names(spells)
        if len(spell_names) == 0:
            return None
        results = drop_down_box(spell_names, max_spells, self.action_id + 2, 16 + self.box_width, SINGLE_ELEMENT)
        if len(results) == 0:
            return None
        result_id = results[0]
        return CastSpellAction(self, 'c', 'VA', self.get_player(), self.get_enemy(), spells[result_id])

    def get_enemy_action(self):
        enemy = self.get_enemy()
        if enemy.range >= self.distance:
            return AttackPlayerAction(self, enemy, self.get_player())
        # can't attack, then move towards the player
        if enemy.has_status('fast') and self.distance > 3:
            return MoveAction(self, 'a', '-', enemy, self.get_player(), 3)
        if not enemy.has_status('slow') and self.distance > 2:
            return MoveAction(self, 'a', '-', enemy, self.get_player(), 2)
        if self.distance > 1:
            return MoveAction(self, 'a', '-', enemy, self.get_player(), 1)
        return WaitAction(self, '?', enemy)

    def player_won(self):
        rewards = self.get_enemy().get_rewards(self.config_file)

        display_names = []
        g = rewards['gold']
        display_names += [f'#yellow-black {g} #normal gold']
        # for item in rewards['items']:
        #     display_names += [item.name]
        # for item in rewards['countable_items']:
        #     display_names += [f'{item.name} (amount: {item.amount})']
        for item in rewards['items']:
            display_names += [item.get_cct_display_text()]
        for item in rewards['countable_items']:
            display_names += [item.get_cct_display_text()]

        r_w_height = self.HEIGHT - 2
        r_w_width = max(self.WIDTH // 3, max([cct_len(n) for n in display_names])) + 1
        
        limit = r_w_height - 3
        page = 0

        rewards_window = curses.newwin(r_w_height, r_w_width, 1, 1)
        rewards_window.keypad(1)
        draw_borders(rewards_window)
        rewards_window.addstr(0, 1, 'End of combat')
        rewards_window.refresh()
        rewards_window.addstr(1, 1, 'Rewards:')

        while True:
            y = 1
            # clear display
            for i in range(limit):
                rewards_window.addstr(y + i + 1, 1, ' ' * (r_w_width - 2))
            rewards_window.addch(2, r_w_width - 1, curses.ACS_VLINE)
            rewards_window.addch(r_w_height - 2, r_w_width - 1, curses.ACS_VLINE)

            # display
            first = 0
            last = len(display_names) - 1
            if len(display_names) > limit:
                first = page
                last = page + limit - 1
            for i in range(first, last + 1):
                put(rewards_window, 1 + y, 3, display_names[i])
                y += 1
            if len(display_names) > limit:
                if page != 0:
                    rewards_window.addch(2, r_w_width - 1, curses.ACS_UARROW)
                if page != len(display_names) - limit:
                    rewards_window.addch(r_w_height - 2, r_w_width - 1, curses.ACS_DARROW)
            
            # key processing
            key = rewards_window.getch()
            if key == 259: # UP
                if len(display_names) > limit:
                    page -= 1
                    if page < 0:
                        page = 0
            if key == 258: # DOWN
                if len(display_names) > limit:
                    page += 1
                    if page > len(display_names) - limit:
                        page = len(display_names) - limit
            if key == 27 or key == 10 or key == 32: # ESC/ENTER/SPACE
                break

        # at the end
        self.get_player().add_rewards(rewards)

    def player_lost(self):
        pass

    def index_by_key(self, key):
        c = chr(key)
        for i in range(len(self.player_actions)):
            if self.player_actions[i].char == c:
                return i
        return -1