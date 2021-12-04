import curses

from cursesui.Utility import cct_real_str, draw_borders, draw_separator, message_box, put

class Trade:
    def __init__(self, parent, player, vendor_name, vendor_gold, vendor_items):
        self.parent = parent
        self.HEIGHT, self.WIDTH = parent.window.getmaxyx()

        self.player = player
        self.vendor_name = vendor_name
        self.vendor_gold = vendor_gold
        self.vendor_items = vendor_items

        self.choice = 0
        self.selling = True
        self.info_window_selected = False
        self.bought_item_ids = []
        self.sold_item_ids = []
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
                break
            if key == 63: # ?
                self.display_current_item_description()
            if key == 32: # SPACE
                self.move_selected_item()
            if key == 9: # TAB
                self.switch_selected_mode()
            if key == 260 or key == 261: # LEFT
                self.switch_selected_window()
            if key == 261: # RIGHT
                pass
            if key == 259: # UP
                self.move_up()
            if key == 258: # DOWN
                self.move_down()
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
                answer = message_box(self.parent, 'Finish trading?', ['Yes', 'No'])
                if answer == 'Yes':
                    # end trading
                    break
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

    def move_selected_item(self):
        # TO-DO: This is horribly unoptimized
        if self.selling:
            if not self.info_window_selected:
                # player window is selected
                if self.choice in self.sold_item_ids:
                    self.sold_item_ids.remove(self.choice)
                else:
                    self.sold_item_ids += [self.choice]
            else:
                # player info window is selected
                self.choice = 0
                self.sold_item_ids.remove(self.sold_item_ids[self.choice])
        else:
            if not self.info_window_selected:
                # vendor window is selected
                if self.choice in self.bought_item_ids:
                    self.bought_item_ids.remove(self.choice)
                else:
                    self.bought_item_ids += [self.choice]
            else:
                # vendor info window is selected
                self.choice = 0
                self.bought_item_ids.remove(self.bought_item_ids[self.choice])
            
    def get_selected_item(self):
        # TO-DO: This is horribly unoptimized
        if self.selling:
            if not self.info_window_selected:
                # player window is selected
                return self.get_player_items()[self.choice]
            else:
                # player info window is selected
                return self.get_player_items()[self.sold_item_ids[self.choice]]
        else:
            if not self.info_window_selected:
                # vendor window is selected
                return self.vendor_items[self.choice]
            else:
                # vendor info window is selected
                return self.vendor_items[self.bought_item_ids[self.choice]]
        return None  

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

    def get_player_items(self):
        # return self.player.items + self.player.countable_items
        return self.player.items

    def get_item_display_names(self, items, buying):
        result = []
        for item in items:
            cost = item.get_buy_price() if buying else item.get_sell_price()
            result += [f'{item.name} (#yellow-black {cost} #normal gold)']
        return result

    def get_sold_value(self):
        result = 0
        player_items = self.get_player_items()
        for i in self.sold_item_ids:
            result += player_items[i].get_sell_price()
        return result

    def get_bought_value(self):
        result = 0
        for i in self.bought_item_ids:
            result += self.vendor_items[i].get_buy_price()
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
        display_names = self.get_item_display_names(self.get_player_items(), False)
        if flag:
            self.max_amount = len(display_names)
        for i in range(len(display_names)):
            color = '#cyan-black' if i in self.sold_item_ids else '#normal'
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.player_window, 2 + i, 2, f'{color} {cct_real_str(display_names[i]) if i in self.sold_item_ids else display_names[i]}', attr)

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
        display_names = self.get_item_display_names(self.vendor_items, True)
        if flag:
            self.max_amount = len(display_names)
        for i in range(len(display_names)):
            color = '#cyan-black' if i in self.bought_item_ids else '#normal'
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.vendor_window, 2 + i, 2, f'{color} {cct_real_str(display_names[i]) if i in self.bought_item_ids else display_names[i]}', attr)
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
        player_items = self.get_player_items()
        for i in range(len(player_items)):
            if i in self.sold_item_ids:
                items += [player_items[i]]
        display_names = self.get_item_display_names(items, False)
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
        v_items = list(self.vendor_items)
        items = []
        for i in range(len(v_items)):
            if i in self.bought_item_ids:
                items += [v_items[i]]
        display_names = self.get_item_display_names(items, True)
        if flag:
            self.max_amount = len(display_names)
        for i in range(len(display_names)):
            attr = curses.A_REVERSE if flag and self.choice == i else 0
            put(self.vendor_info_window, 2 + i, 2, display_names[i], attr)
