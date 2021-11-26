import curses

from ui.Utility import draw_borders

from Utility import str_smart_split

SPACING = 1

class SettingsItem:
    def __init__(self, parent, name, description):
        self.name = name
        self.description = description
        self.w = parent

        self.W_WIDTH = parent.WIDTH

    def get_description(self):
        return self.description

    def draw(self, y, selected):
        if selected:
            self.w.addstr(y, 0, f'> {self.name}')
        else:
            self.w.addstr(y, 0, self.name)

    def proc_key(self, key):
        pass

    def get_value(self):
        return None

class NumericSettingsItem(SettingsItem):
    def __init__(self, parent, name, description, min, max):
        super().__init__(parent, name, description)
        self.value = min
        self.min = min
        self.max = max

        self.x = self.W_WIDTH - len(str(self.max)) - 6

    def get_description(self):
        result = super().get_description()
        result += f' Min: {self.min}, Max: {self.max}'
        return result

    def draw(self, y, selected):
        super().draw(y, selected)
        attr = 0
        if selected:
            attr = curses.A_REVERSE
        self.w.addstr(y, self.x, '<', attr)
        self.w.addstr(y, self.x + 1, str(self.value))
        self.w.addstr(y, self.x + 1 + len(str(self.max)), '>', attr)

    def proc_key(self, key):
        if key == 260: # LEFT
            self.value -= 1
            if self.value < self.min:
                self.value = self.min
        if key == 261: # RIGHT
            self.value += 1
            if self.value > self.max:
                self.value = self.max

    def get_value(self):
        return self.value

class StringSettingsItem(SettingsItem):
    def __init__(self, parent, name, description, max_len):
        super().__init__(parent, name, description)
        self.max_len = max_len
        self.value = 'oichii'
        self.x = self.W_WIDTH - self.max_len - 4

    def get_description(self):
        result = super().get_description()
        result += f' Max length: {self.max_len}'
        return result

    def draw(self, y, selected):
        super().draw(y, selected)
        attr = 0
        if selected:
            attr = curses.A_REVERSE
        self.w.addstr(y, self.x, self.value, attr)
        blank_space = '_' * (self.max_len - len(self.value))
        self.w.addstr(y, self.x + len(self.value), blank_space, attr)

    def get_value(self):
        return self.value

    def proc_key(self, key):
        if key == 10: # ENTER
            curses.flash()

class MultipleOptionsSettingsMenu(SettingsItem):
    def __init__(self, parent, name, description, options):
        super().__init__(parent, name, description)
        self.choice = 0
        self.options = options
        self.max_len = max([len(o) for o in options])
        self.x = self.W_WIDTH - self.max_len - 6

    def get_description(self):
        result = super().get_description()
        result += f' Options: {self.options[0]}'
        for i in range(1, len(self.options)):
            result += f', {self.options[i]}'
        return result

    def draw(self, y, selected):
        super().draw(y, selected)
        attr = 0
        if selected:
            attr = curses.A_REVERSE
        self.w.addstr(y, self.x, '<', attr)
        self.w.addstr(y, self.x + 1, self.options[self.choice])
        self.w.addstr(y, self.x + 1 + self.max_len, '>', attr)

    def proc_key(self, key):
        if key == 260: # LEFT
            self.choice -= 1
            if self.choice < 0:
                self.choice = len(self.options) - 1
        if key == 261: # RIGHT
            self.choice += 1
            if self.choice >= len(self.options):
                self.choice = 0

    def get_value(self):
        return self.options[self.choice]

class SettingsTab:
    def __init__(self, window, name, y, x):
        self.name = name
        self.w = window
        a, b = window.getmaxyx()
        self.WIDTH = b
        self.y = y
        self.x = x

        self.choice = 0
        self.items = []

    def addstr(self, y, x, message, attr=0):
        self.w.addstr(self.y + y, self.x + x, message, attr)

    def draw(self):
        for i in range(len(self.items)):
            self.items[i].draw(SPACING * i, i == self.choice)
        self.w.refresh()

    def proc_key(self, key):
        if key == 259: # UP
            self.choice -= 1
            if self.choice < 0:
                self.choice = len(self.items) - 1
        if key == 258: # DOWN
            self.choice += 1
            if self.choice == len(self.items):
                self.choice = 0
        if self.get_selected_item() != None:
            self.get_selected_item().proc_key(key)

    def get_selected_item(self):
        if len(self.items) == 0:
            return None
        return self.items[self.choice]

class SettingsMenu:
    def draw_borders(self, w):
        w.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def __init__(self, window, config_file):
        super().__init__()
        self.w = window
        self.HEIGHT, self.WIDTH = window.getmaxyx()
        self.config_file = config_file

        self.description_height = 2
        self.tab_i = 0
        self.selected_tab = None

        self.init_tabs()
        self.main_loop()

    def init_tabs(self):
        y = 7
        x = 2

        self.max_name_length = 10

        self.min_game_speed = 1
        self.max_game_speed = 10

        prop_options = ['Ooh', 'When', 'you\'re', 'cold', 'I\'ll be there', 'hold you tight', 'to me']

        game_values_tab = SettingsTab(self.w, 'Game values', y, x)
        game_values_tab.items += [StringSettingsItem(game_values_tab, 'Default character name', 'The default name of your character.', self.max_name_length)]
        game_values_tab.items += [NumericSettingsItem(game_values_tab, 'Game speed', 'The speed of the game', self.min_game_speed, self.max_game_speed)]
        game_values_tab.items += [MultipleOptionsSettingsMenu(game_values_tab, "Prop values", "Just some random values lmao.", prop_options)]

        path_tab = SettingsTab(self.w, 'Paths', y, x)
        game_values_tab.items += []

        self.tabs = [game_values_tab, path_tab]

    def draw_description(self):
        # clear description window
        for i in range(self.description_height):
            self.w.addstr(3 + i, 1, ' ' * (self.WIDTH - 2))
        if self.selected_item != None:
            # draw description
            desc = self.selected_item.get_description()
            lines = str_smart_split(desc, self.WIDTH - 2)
            for i in range(len(lines)):
                self.w.addstr(3 + i, 1, lines[i])

    def draw_tabs(self):
        x = 2
        for i in range(len(self.tabs)):
            tab_name = f'[{self.tabs[i].name}]'
            if i == self.tab_i:
                self.w.addstr(5, x, tab_name, curses.A_REVERSE)
            else:
                self.w.addstr(5, x, tab_name)
            x += 2 + len(tab_name)

    def draw(self):
        draw_borders(self.w)
        self.w.addstr(1, 1, 'Settings')
        # draw menu name and description separator
        self.w.addch(2, 0, curses.ACS_LTEE)
        self.w.addch(2, self.WIDTH - 1, curses.ACS_RTEE)
        for i in range(1, self.WIDTH - 1):
            self.w.addch(2, i, curses.ACS_HLINE)
        # draw description
        self.draw_description()
        # draw description and setting items separator
        self.w.addch(3 + self.description_height, 0, curses.ACS_LTEE)
        self.w.addch(3 + self.description_height, self.WIDTH - 1, curses.ACS_RTEE)
        for i in range(1, self.WIDTH - 1):
            self.w.addch(3 + self.description_height, i, curses.ACS_HLINE)
        # draw tabs
        self.draw_tabs()
        self.w.refresh()

    def main_loop(self):
        self.selected_item = None
        self.selected_tab = self.tabs[self.tab_i]
        while True:
            self.selected_item = self.selected_tab.get_selected_item()
            # display
            self.draw()
            self.selected_tab.draw()
            # key processing
            key = self.w.getch()
            if key == 81: # Q
                return
            if key == 353: # SHIFT+TAB
                self.tab_i -= 1
                if self.tab_i < 0:
                    self.tab_i = len(self.tabs) - 1
                self.selected_tab = self.tabs[self.tab_i]
            if key == 9: # TAB
                self.tab_i += 1
                if self.tab_i == len(self.tabs):
                    self.tab_i = 0
                self.selected_tab = self.tabs[self.tab_i]
            self.selected_tab.proc_key(key)
            
            # clear screen
            self.w.clear()
        