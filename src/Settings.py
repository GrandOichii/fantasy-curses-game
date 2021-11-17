import curses

class SettingsItem:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def get_description(self):
        return self.description

class MultipleOptionsSettingsMenu(SettingsItem):
    def __init__(self, name, description, options):
        super().__init__(name, description)
        self.options = options

    def get_description(self):
        result = super().get_description()
        result += f'Options: {self.options[0]}'
        for i in range(1, len(self.options)):
            result += self.options[i]
        return result

class SettingsTab:
    def __init__(self, window, name):
        self.name = name
        self.window = window

class SettingsMenu:
    def draw_borders(self, w):
        w.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def __init__(self, window, config_file):
        super().__init__()
        self.w = window
        self.HEIGHT, self.WIDTH = window.getmaxyx()
        self.config_file = config_file

        self.description_height = 2

        self.init_tabs()
        self.main_loop()

    def init_tabs(self):
        path_tab = SettingsTab(self.w, 'Paths')
        self.tabs = [path_tab]

    def draw_description(self):
        y_start = 3
        for i in range(self.description_height):
            self.w.addstr(3 + i, 1, 'a' * (self.WIDTH - 2))
        if self.selected_item != None:
            # draw description
            a=1
        

    def draw(self):
        self.draw_borders(self.w)
        self.w.addstr(1, 1, 'Settings')
        # draw menu name and description separator
        self.w.addch(2, 0, curses.ACS_LTEE)
        self.w.addch(2, self.WIDTH - 1, curses.ACS_RTEE)
        for i in range(1, self.WIDTH - 1):
            self.w.addch(2, i, curses.ACS_HLINE)
        # draw description
        self.draw_description()
        # draw description and setting items separatorself.w.addch(2, 0, curses.ACS_LTEE)
        self.w.addch(3 + self.description_height, self.WIDTH - 1, curses.ACS_RTEE)
        for i in range(1, self.WIDTH - 1):
            self.w.addch(3 + self.description_height, i, curses.ACS_HLINE)
        # self.w.addch()
        self.w.refresh()

    def main_loop(self):
        self.selected_item = None
        tab_i = 0
        while True:
            # display
            self.draw()
            # key processing
            key = self.w.getch()
            if key == 81: # Q
                return
            if key == 260: # LEFT
                tab_i -= 1
                if tab_i < 0:
                    tab_i = len(self.tabs) - 1
            if key == 261: # RIGHT
                tab_i += 1
                if tab_i == len(self.tabs):
                    tab_i = 0
            # clear screen
            self.w.clear()
        