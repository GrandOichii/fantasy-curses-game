import curses

class Button:
    def __init__(self, name, text: str, parent):
        self.name = name
        self.text = text
        parent.add_button(self)
        self.leads_to = 0

    def connect_to(self, menu):
        self.leads_to = menu

class ActionButton(Button):
    def __init__(self, name, text: str, parent, action):
        super().__init__(name, text, parent)
        self.action = action
    
    def click(self):
        self.action()

class DropDownBox:
    SIGNLE_ELEMENT = 1
    MULTIPLE_ELEMENTS = 2

    def draw_borders(self):
        self.window.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

    def __init__(self, options, max_display_amount, y, x, choice_type):
        self.options = options
        self.choice_type = choice_type
        self.max_display_amount = max_display_amount
        self.HEIGHT = max_display_amount + 2
        self.WIDTH = max([len(o) for o in options]) + 2

        self.window = curses.newwin(self.HEIGHT, self.WIDTH, y, x)
        self.window.keypad(1)

    def show(self):
        results = set()
        indexes = [i for i in range(len(self.options))]
        cursor = 0
        page_n = 0
        choice = 0
        self.draw_borders()
        while True:
            # clear lines
            self.window.addch(1, self.WIDTH - 1, curses.ACS_VLINE)
            self.window.addch(self.HEIGHT - 2, self.WIDTH - 1, curses.ACS_VLINE)
            for i in range(1, self.HEIGHT - 1):
                self.window.addstr(i, 1, ' ' * (self.WIDTH - 2))
            # display
            if len(self.options) > self.max_display_amount:
                if page_n != 0:
                    self.window.addch(1, self.WIDTH - 1, curses.ACS_UARROW)
                if page_n != len(self.options) - self.max_display_amount:
                    self.window.addch(self.HEIGHT - 2, self.WIDTH - 1, curses.ACS_DARROW)
            for i in range(min(self.max_display_amount, len(self.options))):
                if i == cursor:
                    self.window.addstr(1 + i, 1, self.options[i + page_n], curses.A_REVERSE)
                else:
                    self.window.addstr(1 + i, 1, self.options[i + page_n])
            # key processing
            key = self.window.getch()
            if key == 27: # ESC
                break
            if key == 259: # UP
                choice -= 1
                cursor -= 1
                if cursor < 0:
                    if len(self.options) > self.max_display_amount:
                        if page_n == 0:
                            cursor = self.max_display_amount - 1
                            choice = len(self.options) - 1
                            page_n = len(self.options) - self.max_display_amount
                        else:
                            page_n -= 1
                            cursor += 1
                    else:
                        cursor = len(self.options) - 1
                        choice = cursor
            if key == 258: # DOWN
                choice += 1
                cursor += 1
                if len(self.options) > self.max_display_amount:
                    if cursor >= self.max_display_amount:
                        cursor -= 1
                        page_n += 1
                        if choice == len(self.options):
                            choice = 0
                            cursor = 0
                            page_n = 0
                else:
                    if cursor >= len(self.options):
                        cursor = 0
                        choice = 0
            if key == 10: # ENTER
                results.add(indexes[choice])
                if self.choice_type == DropDownBox.SIGNLE_ELEMENT:
                    break
                if choice == -1:
                    break
                self.options.pop(choice)
                indexes.pop(choice)
                if len(self.options) > self.max_display_amount:
                    if page_n == len(self.options) - self.max_display_amount + 1:
                        page_n -= 1
                        choice -= 1
                else:
                    if page_n == 1:
                        page_n = 0
                        choice -= 1
                    if choice == len(self.options):
                        cursor -= 1
                        choice -= 1
                    pass
        return list(results)