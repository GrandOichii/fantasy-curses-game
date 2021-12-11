import curses
from cursesui.Elements import Window

from cursesui.Utility import cct_len, cct_real_str, draw_borders, draw_separator, message_box, put, show_controls_window
from gamelib.Entities import Player
from gamelib.Items import CountableItem, Item

class Trade:
    controls = {
        "Move selected cursor": "UP/DOWN",
        "Switch windows": "LEFT/RIGHT",
        "Sell/Buy item": "SPACE",
        "Finish trading": "ENTER",
        "Cancel trading": "ESC",
        "Switch modes": "TAB",
        "Open item description": "D",
    }

    def __init__(self, parent: Window, player: Player, vendor_name: str, vendor_gold: int, vendor_items: list[Item], vendor_countable_items: list[CountableItem]):
        self.parent = parent
        self.HEIGHT, self.WIDTH = parent.window.getmaxyx()

        self.player = player
        self.vendor_name = vendor_name
        self.vendor_gold = vendor_gold
        self.vendor_items = list(vendor_items)
        self.vendor_countable_items = []
        for item in vendor_countable_items:
            self.vendor_countable_items += [item.copy()]

        self.player_items = list(player.items)
        self.player_countable_items = []
        for item in player.countable_items:
            self.player_countable_items += [item.copy()]

        self.choice = 0
        self.selling = True
        self.info_window_selected = False
        self.bought_item_ids = []
        self.sold_item_ids = []
        self.bought_countable_item_amounts = {}
        for i in range(len(self.vendor_countable_items)):
            self.bought_countable_item_amounts[i] = 0
        self.sold_countable_item_amounts = {}
        for i in range(len(self.player_countable_items)):
            self.sold_countable_item_amounts[i] = 0
        self.max_amount = 0

        self.player_window_height = self.HEIGHT
        self.player_window_width = self.WIDTH // 3
        self.player_window = curses.newwin(self.player_window_height, self.player_window_width, 0, 0)
        self.player_window.keypad(1)

        self.vendor_window_height = self.HEIGHT
        self.vendor_window_width = self.player_window_width
        self.vendor_window = curses.newwin(self.vendor_window_height, self.vendor_window_width, 0, self.WIDTH - self.player_window_width)

        self.player_info_window_height = self.HEIGHT // 2 - 1
        self.player_info_window_width = self.WIDTH - 2 * self.player_window_width
        self.player_info_window = curses.newwin(self.player_info_window_height, self.player_info_window_width, 0, self.player_window_width)

        self.vendor_info_window_height = self.HEIGHT - self.player_info_window_height
        self.vendor_info_window_width = self.player_info_window_width
        self.vendor_info_window = curses.newwin(self.vendor_info_window_height, self.vendor_info_window_width, self.player_info_window_height, self.player_window_width)

    def get_key(self):
        return self.player_window.getch()

    def start(self):
        # TO-DO: find a way to change the format of while loop without the "Not enough gold" message dissapearing
        key = -1
        self.draw()
        while True:
            # key handling
            key = self.get_key()
            if key == 27: # ESC
                return False
            if key == 68: # D
                self.display_current_item_description()
            if key == 32: # SPACE
                self.move_selected_item()
            if key == 9: # TAB
                self.switch_selected_mode()
            if key == 260 or key == 261: # LEFT/RIGHT
                self.switch_selected_window()
            if key == 259: # UP
                self.move_up()
            if key == 258: # DOWN
                self.move_down()
            if key == 63: # ?
                show_controls_window(self.parent, Trade.controls)
            if key == 10: # ENTER
                # finish trading
                if self.get_player_final_gold() < 0:
                    put(self.player_window, self.player_window_height - 3, 1, f'#black-red Not enough gold')
                    self.player_window.refresh()
                    continue
                if self.get_vendor_final_gold() < 0:
                    put(self.vendor_window, self.vendor_window_height - 3, 1, f'#black-red Not enough gold')
                    self.vendor_window.refresh()
                    continue
                answer = message_box(self.parent, 'Finish trading?', ['No', 'Yes'])
                if answer == 'Yes':
                    # end trading
                    return True
            # draw
            self.draw()        

    def move_up(self):
        self.choice -= 1
        if self.choice < 0:
            self.choice = self.max_amount - 1

    def move_down(self):
        self.choice += 1
        if self.choice >= self.max_amount:
            self.choice = 0

    def switch_selected_window(self):
        # TO-DO: disable user from switching to blank window
        self.info_window_selected = not self.info_window_selected
        self.choice = 0
            
    def switch_selected_mode(self):
        # TO-DO: disable user from switching to blank window
        self.selling = not self.selling
        self.info_window_selected = False
        self.choice = 0

    def request_amount(self, item: Item, buying: bool):
        result = 0
        price = item.get_buy_price() if buying else item.get_sell_price()
        top = '#yellow-black {}#normal : {} (#yellow-black {} #normal gold per piece)'.format('Buying' if buying else 'Selling', item.name, price)
        pfg = self.get_player_final_gold()
        # amount window
        window_height = 7
        window_width = cct_len(top) + 2
        window_y = self.HEIGHT // 2 - window_height // 2
        window_x = self.WIDTH // 2 - window_width // 2
        window = curses.newwin(window_height, window_width, window_y, window_x)
        window.keypad(1)
        while True:
            # draw
            window.clear()
            draw_borders(window)
            put(window, 0, 1, '#magenta-black Select amount')
            put(window, 1, 1, top)
            fp = pfg
            mult = price * result
            if buying:
                fp -= mult
            else:
                fp += mult
            bottom = '#yellow-black {} #normal {} #black-white <#normal {}#black-white >#normal  x #yellow-black {} #normal = #{} {}'.format(
                pfg, 
                '-' if buying else '+', 
                result, 
                price, 
                'red-black' if fp < 0 else 'yellow-black', 
                fp)
            put(window, 2, window_width // 2 - cct_len(bottom) // 2, bottom)
            window.refresh()
            # 
            key = self.get_key()
            if key == 27: # ESC
                return 0
            if key == 261: # RIGHT
                if result < item.amount:
                    result += 1
            if key == 260: # LEFT
                if result > 0:
                    result -= 1
            if key == 10: # ENTER
                break
        return result

    def move_selected_item(self):
        # TO-DO: This is ugly
        # item = self.get_selected_item()
        if self.selling:
            # player windows
            if not self.info_window_selected:
                # player window is selected
                if self.choice >= len(self.player_items):
                    # countable item
                    index = self.choice - len(self.player_items)
                    item = self.get_selected_item()
                    if self.sold_countable_item_amounts[index] != 0:
                        item.amount += self.sold_countable_item_amounts[index]
                        self.sold_countable_item_amounts[index] = 0
                    else:
                        amount = self.request_amount(item, False)
                        item.amount -= amount
                        self.sold_countable_item_amounts[index] += amount
                else:
                    # normal item
                    if self.choice in self.sold_item_ids:
                        self.sold_item_ids.remove(self.choice)
                    else:
                        self.sold_item_ids += [self.choice]
                        self.sold_item_ids = sorted(self.sold_item_ids)
            else:
                # player info window is selected
                if self.choice >= len(self.sold_item_ids):
                    # countable item
                    offset = self.get_offset(self.sold_countable_item_amounts, self.choice - len(self.sold_item_ids))
                    id = self.choice - len(self.sold_item_ids) + offset
                    item = self.player_countable_items[id]
                    item.amount += self.sold_countable_item_amounts[id]
                    self.sold_countable_item_amounts[id] = 0
                else:
                    # normal item
                    self.sold_item_ids.remove(self.sold_item_ids[self.choice])
                self.choice = 0
        else:
            # vendor windows
            if not self.info_window_selected:
                # vendor window is selected
                if self.choice >= len(self.vendor_items):
                    # countable item
                    index = self.choice - len(self.vendor_items)
                    item = self.get_selected_item()
                    if self.bought_countable_item_amounts[index] != 0:
                        item.amount += self.bought_countable_item_amounts[index]
                        self.bought_countable_item_amounts[index] = 0
                    else:
                        amount = self.request_amount(item, True)
                        item.amount -= amount
                        self.bought_countable_item_amounts[index] += amount
                else:
                    # normal item
                    if self.choice in self.bought_item_ids:
                        self.bought_item_ids.remove(self.choice)
                    else:
                        self.bought_item_ids += [self.choice]
                        self.bought_item_ids = sorted(self.bought_item_ids)
            else:
                # vendor info window is selected
                if self.choice >= len(self.bought_item_ids):
                    # countable item
                    offset = self.get_offset(self.bought_countable_item_amounts, self.choice - len(self.bought_item_ids))
                    id = self.choice - len(self.bought_item_ids) + offset
                    item = self.vendor_countable_items[id]
                    item.amount += self.bought_countable_item_amounts[id]
                    self.bought_countable_item_amounts[id] = 0
                else:
                    # normal item
                    self.bought_item_ids.remove(self.bought_item_ids[self.choice])
                self.choice = 0

    def get_offset(self, d: dict, to: int):
        result = 0
        values = list(d.values())
        for i in range(to + 1):
            if values[i] == 0:
                result += 1
        # for key in d:
        #     if d[key] == 0:
        #         result += 1
        return result

    def get_player_item(self, id: int):
        l = len(self.player_items)
        if id >= l:
            # select countable item
            id -= l
            return self.player_countable_items[id]
        # select normal item
        return self.player_items[id]

    def get_vendor_item(self, id: int):
        l = len(self.vendor_items)
        if id >= l:
            # select countable item
            id -= l
            return self.vendor_countable_items[id]
        # select normal item
        return self.vendor_items[id]

    def get_sold_item(self, choice: int):
        l = len(self.sold_item_ids)
        if choice >= l:
            return self.get_player_item(choice + len(self.player_items) - l)
        return self.get_player_item(self.sold_item_ids[choice])

    def get_bought_item(self, choice: int):
        l = len(self.bought_item_ids)
        if choice >= l:
            return self.get_vendor_item(choice + len(self.vendor_items) - l)
        return self.get_vendor_item(self.bought_item_ids[choice])

    def get_selected_item(self):
        # TO-DO: This is horribly unoptimized
        if self.selling:
            if not self.info_window_selected:
                # player window is selected
                return self.get_player_item(self.choice)
            else:
                # player info window is selected
                return self.get_sold_item(self.choice)
        else:
            if not self.info_window_selected:
                # vendor window is selected
                return self.get_vendor_item(self.choice)
            else:
                # vendor info window is selected
                return self.get_bought_item(self.choice)

    def display_current_item_description(self):
        item = self.get_selected_item()
        if item == None:
            return
        window_height = self.HEIGHT - 4
        window_width = self.WIDTH // 4 * 3
        window_y = self.HEIGHT // 2 - window_height // 2
        window_x = self.WIDTH // 2 - window_width // 2
        window = curses.newwin(window_height, window_width, window_y, window_x)
        window.keypad(1)

        desc = item.get_description(window_width - 2)
        while True:
            # display
            window.clear()
            draw_borders(window)
            put(window, 0, 1, f'#yellow-black Item description')
            for i in range(len(desc)):
                put(window, i + 1, 1, desc[i])
            window.refresh()

            key = self.get_key()
            if key == 27 or key == 32: # ESC/SPACE
                break

    def get_item_display_names(self, items: list[Item], buying: bool):
        result = []
        for item in items:
            cost = item.get_buy_price() if buying else item.get_sell_price()
            if isinstance(item, CountableItem):
                result += [f'{item.name} x#magenta-black {item.amount} #normal (#yellow-black {cost} #normal gold per piece)']
            else:
                result += [f'{item.name} (#yellow-black {cost} #normal gold)']
        return result

    def get_sold_value(self):
        result = 0
        for i in self.sold_item_ids:
            result += self.player_items[i].get_sell_price()
        for key in self.sold_countable_item_amounts:
            result += self.player_countable_items[key].get_sell_price() * self.sold_countable_item_amounts[key]
        return result

    def get_bought_value(self):
        result = 0
        for i in self.bought_item_ids:
            result += self.vendor_items[i].get_buy_price()
        for key in self.bought_countable_item_amounts:
            result += self.vendor_countable_items[key].get_buy_price() * self.bought_countable_item_amounts[key]
        return result
    
    def get_player_final_gold(self):
        return self.player.gold + self.get_sold_value() - self.get_bought_value()

    def get_vendor_final_gold(self):
        return self.vendor_gold - self.get_sold_value() + self.get_bought_value()

    # draw

    def draw(self):
        self.draw_player_window()
        self.draw_vendor_window()
        self.draw_player_info_window()
        self.draw_vendor_info_window()

        self.player_window.refresh()
        self.vendor_window.refresh()
        self.player_info_window.refresh()
        self.vendor_info_window.refresh()

    def draw_player_window(self):
        self.player_window.clear()
        draw_borders(self.player_window, 'black-white' if self.selling else 'normal')
        put(self.player_window, 0, 1, f'#green-black {self.player.name} #normal items')

        # display items
        flag = self.selling and not self.info_window_selected
        display_names = self.get_item_display_names(self.player_items + self.player_countable_items, False)
        if flag:
            self.max_amount = len(display_names)
        HCOLOR = '#cyan-black'
        for i in range(len(display_names)):
            color = '#normal'
            item = self.get_player_item(i)
            if isinstance(item, CountableItem):
                if self.sold_countable_item_amounts[i - len(self.player_items)] != 0:
                    color = HCOLOR
            elif i in self.sold_item_ids:
                color = HCOLOR
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.player_window, 2 + i, 2, f'{color} {cct_real_str(display_names[i]) if color == HCOLOR else display_names[i]}', attr)

        # draw gold info
        draw_separator(self.player_window, self.player_window_height - 3, 'black-white' if self.selling else 'normal')
        gold_str = f'Gold: #yellow-black {self.player.gold} '
        sold_value = self.get_sold_value()
        if sold_value != 0:
            gold_str += f'#normal + #yellow-black {sold_value} '
        bought_value = self.get_bought_value()
        if bought_value != 0:
            gold_str += f'#normal - #yellow-black {bought_value} '
        final_value = self.player.gold + sold_value - bought_value
        if final_value != self.player.gold:
            gold_str += '#normal = #{} {}'.format('red-black' if final_value < 0 else 'yellow-black', final_value)
        put(self.player_window, self.player_window_height - 2, 1, gold_str)

    def draw_vendor_window(self):
        self.vendor_window.clear()
        draw_borders(self.vendor_window, 'black-white' if not self.selling else 'normal')
        put(self.vendor_window, 0, 1, f'#cyan-black {self.vendor_name} #normal items')

        # display items
        flag = not self.selling and not self.info_window_selected
        display_names = self.get_item_display_names(self.vendor_items + self.vendor_countable_items, True)
        if flag:
            self.max_amount = len(display_names)
        HCOLOR = '#cyan-black'
        for i in range(len(display_names)):
            color = '#normal'
            item = self.get_vendor_item(i)
            if isinstance(item, CountableItem):
                if self.bought_countable_item_amounts[i - len(self.vendor_items)] != 0:
                    color = HCOLOR
            elif i in self.bought_item_ids:
                color = HCOLOR
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.vendor_window, 2 + i, 2, f'{color} {cct_real_str(display_names[i]) if color == HCOLOR else display_names[i]}', attr)
        # draw gold info
        draw_separator(self.vendor_window, self.vendor_window_height - 3, 'black-white' if not self.selling else 'normal')
        gold_str = f'Gold: #yellow-black {self.vendor_gold} '
        sold_value = self.get_sold_value()
        if sold_value != 0:
            gold_str += f'#normal - #yellow-black {sold_value} '
        bought_value = self.get_bought_value()
        if bought_value != 0:
            gold_str += f'#normal + #yellow-black {bought_value} '
        final_value = self.vendor_gold + bought_value - sold_value
        if final_value != self.vendor_gold:
            gold_str += '#normal = #{} {}'.format('red-black' if final_value < 0 else 'yellow-black', final_value)
        put(self.vendor_window, self.vendor_window_height - 2, 1, gold_str)

    def draw_player_info_window(self):
        self.player_info_window.clear()
        draw_borders(self.player_info_window, 'black-white' if self.selling else 'normal')
        put(self.player_info_window, 0, 1, f'#yellow-black Selling')

        # display items
        flag = self.selling and self.info_window_selected
        items = []
        for i in range(len(self.player_items)):
            if i in self.sold_item_ids:
                items += [self.player_items[i]]
        c_items = []
        for key in self.sold_countable_item_amounts:
            amount = self.sold_countable_item_amounts[key]
            if amount > 0:
                item = self.player_countable_items[key].copy()
                item.amount = self.sold_countable_item_amounts[key]
                c_items += [item]
        display_names = self.get_item_display_names(items + c_items, False)
        if flag:
            self.max_amount = len(display_names)
        for i in range(len(display_names)):
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.player_info_window, 2 + i, 2, display_names[i], attr)

    def draw_vendor_info_window(self):
        self.vendor_info_window.clear()
        draw_borders(self.vendor_info_window, 'black-white' if not self.selling else 'normal')
        # display 
        put(self.vendor_info_window, 0, 1, f'#yellow-black Buying')
        flag = not self.selling and self.info_window_selected
        items = []
        for i in range(len(self.vendor_items)):
            if i in self.bought_item_ids:
                items += [self.vendor_items[i]]
        # add countable items
        c_items = []
        for key in self.bought_countable_item_amounts:
            amount = self.bought_countable_item_amounts[key]
            if amount > 0:
                item = self.vendor_countable_items[key].copy()
                item.amount = self.bought_countable_item_amounts[key]
                c_items += [item]
        display_names = self.get_item_display_names(items + c_items, True)
        if flag:
            self.max_amount = len(display_names)
        for i in range(len(display_names)):
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.vendor_info_window, 2 + i, 2, display_names[i], attr)
