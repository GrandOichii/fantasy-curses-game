import curses

from cursesui.Utility import draw_borders, draw_separator, message_box, put, init_colors, cct_len, show_controls_window, str_smart_split

class Window:
    def __init__(self, window):
        init_colors()
        self.window = window
        self.HEIGHT, self.WIDTH = window.getmaxyx()
        self.current_menu = None
        self.running = True
        self.window.keypad(1)
        self.initUI()

    def get_window(self):
        return self.window

    def start(self):
        while self.running:
            if self.current_menu:
                self.current_menu.draw()
                key = self.window.getch()
                self.handle_key(key)
                self.current_menu.handle_key(key)

    def exit(self):
        self.running = False

    def initUI(self):
        pass

    def handle_key(self, key):
        pass

class Menu:
    def __init__(self, parent, title):
        self.parent = parent
        self.title = title
        self.elements = []
        self.border_color_pair = 'normal'
        self.bottom_description = ''
        self.controls = {}

    def get_window(self):
        return self.parent.window

    def unfocus_all(self):
        for e in self.elements:
            e.set_focused(False)

    def focus(self, id):
        self.elements[id].set_focused(True)

    def get_focused_element_id(self):
        for i in range(len(self.elements)):
            if self.elements[i].focused:
                return i

    def handle_key(self, key):
        if key == 63: # ?
            self.show_controls()
        element = self.elements[self.get_focused_element_id()]
        element.handle_key(key)

    def add_element(self, element):
        self.elements += [element]

    def draw(self):
        parent_window = self.get_window()
        parent_window.clear()
        draw_borders(parent_window, self.border_color_pair)
        put(parent_window, 1, 1, self.title)
        draw_separator(parent_window, 2, self.border_color_pair)
        for element in self.elements:
            element.draw()
        if self.bottom_description != '':
            self.draw_bottom_description()
        parent_window.refresh()

    def draw_bottom_description(self):
        parent_window = self.get_window()
        lines = str_smart_split(self.bottom_description, self.parent.WIDTH - 2)
        y = self.parent.HEIGHT - len(lines) - 1
        for i in range(len(lines)):
            put(parent_window, y + i, 1, lines[i])

    def show_controls(self):
        if self.controls == {}:
            message_box(self.parent, '#red-black No controls set!', ['Ok'])
        else:
            show_controls_window(self.parent, self.controls)

class UIElement:
    def __init__(self, parent, text):
        self.parent = parent
        self.text = text
        self.focused = False

        self.focused_format = '{}'
        self.focused_attribute = curses.A_REVERSE

        self.y = 0
        self.x = 0

        self.next = None
        self.next_key = 258

        self.prev = None
        self.prev_key = 259

    def set_focused(self, value):
        self.focused = value

    def set_pos(self, y, x):
        self.y = y
        self.x = x

    def draw(self):
        parent_window = self.parent.window
        if self.focused:
            put(parent_window, self.y + 2, self.x + 1, self.focused_format.format(self.text), self.focused_attribute)
        else:
            put(parent_window, self.y + 2, self.x + 1, self.text)

    def handle_key(self, key):
        if key == self.next_key and self.next:
            self.set_focused(False)
            self.next.set_focused(True)
        if key == self.prev_key and self.prev:
            self.set_focused(False)
            self.prev.set_focused(True)

    def draw_width(self):
        return cct_len(self.focused_format.format(self.text))

class Separator(UIElement):
    def __init__(self, parent, y, color_pair='normal'):
        super().__init__(parent, 'ERR')
        self.color_pair = color_pair
        self.y = y

    def draw(self):
        draw_separator(self.parent.get_window(), self.y + 2, self.color_pair)

class Button(UIElement):
    def __init__(self, parent, text, click=None):
        super().__init__(parent, text)
        self.click = click
        self.clickKey = 10

    def handle_key(self, key):
        super().handle_key(key)
        if key == self.clickKey and self.click:
            self.click()

class TextField(UIElement):
    def __init__(self, parent, text, max_width):
        if len(text) > max_width:
            raise Exception('ERR: Starting text in TextField is longer than max_width')
        super().__init__(parent, text)
        self.cursor = len(text)
        self.max_width = max_width
        self.placeholder_char = '_'

    def handle_key(self, key):
        super().handle_key(key)
        if (key == 127 or key == 8) and len(self.text) > 0:
            self.text = self.text[:-1]
            self.cursor -= 1
        if len(self.text) == self.max_width:
            return
        if key >= 97 and key <= 122:
            self.text += chr(key)
            self.cursor += 1
        if key >= 65 and key <= 90:
            self.text += chr(key)
            self.cursor += 1
        if key == 32:
            self.text += ' '
            self.cursor += 1

    def draw(self):
        y = self.y + 2
        x = self.x + 1
        parent_window = self.parent.window
        placeholder = self.placeholder_char * (self.max_width - len(self.text))
        parent_window.addstr(y, x, self.text)
        parent_window.addstr(y, x + len(self.text), placeholder)
        if self.focused:
            char = ' '
            if self.cursor < len(self.text):
                char = self.text[self.cursor]
            parent_window.addch(y, x + self.cursor, char, curses.A_REVERSE)

    def draw_width(self):
        return self.max_width

class NumericLeftRight(UIElement):
    def __init__(self, parent, value, min_val, max_val):
        super().__init__(parent, '')
        self.min_val = min_val
        self.max_val = max_val
        self.value = value

    def handle_key(self, key):
        super().handle_key(key)
        if key == 261 and self.value < self.max_val: # LEFT
            self.value += 1
        if key == 260 and self.value > self.min_val: # RIGHT
            self.value -= 1

    def draw_width(self):
        return len(str(self.max_val)) + 2

    def draw(self):
        y = self.y + 2
        x = self.x + 1
        parent_window = self.parent.window
        placeholder = ' ' * (len(str(self.max_val)) - len(str(self.value)))
        parent_window.addstr(y, x, f'<{self.value}{placeholder}>')
        if self.focused:
            parent_window.addch(y, x, '<', curses.A_REVERSE)
            parent_window.addch(y, x + len(str(self.max_val)) + 1, '>', curses.A_REVERSE)

class WordChoice(UIElement):
    def __init__(self, parent, options, start=0):
        super().__init__(parent, '')
        if start >= len(options):
            raise Exception('ERR: start in WordChoice is bigger than amount of options')
        self.choice = start
        self.options = options
        self.max_width = max([cct_len(o) for o in options])

    def draw(self):
        y = self.y + 2
        x = self.x + 1
        placeholder = ' ' * (self.max_width - cct_len(self.options[self.choice]))
        parent_window = self.parent.window
        put(parent_window, y, x, f'<{self.options[self.choice]}{placeholder}>')
        if self.focused:
            parent_window.addch(y, x, '<', curses.A_REVERSE)
            parent_window.addch(y, x + self.max_width + 1, '>', curses.A_REVERSE)

    def handle_key(self, key):
        super().handle_key(key)
        if key == 261 and self.choice < len(self.options) - 1: # LEFT
            self.choice += 1
        if key == 260 and self.choice > 0: # RIGHT
            self.choice -= 1

    def draw_width(self):
        return self.max_width + 2

    def get_selected_value(self):
        return self.options[self.choice]

class Widget(UIElement):
    def __init__(self, parent, stretch=False):
        super().__init__(parent, 'err')
        self.sub_elements = []
        self.distance = 0
        self.focused_element_id = 0
        self.stretch = stretch

    def set_pos(self, y, x):
        super().set_pos(y, x)
        self.distance = 0
        elements = list(self.sub_elements)
        self.sub_elements = []
        for element in elements:
            self.add_element(element)

    def add_element(self, element):
        element.set_pos(self.y, self.x + self.distance)
        self.sub_elements += [element]
        self.distance += 1 + element.draw_width()

    def set_focused(self, value):
        super().set_focused(value)
        self.sub_elements[self.focused_element_id].set_focused(value)

    def handle_key(self, key):
        self.sub_elements[self.focused_element_id].handle_key(key)
        super().handle_key(key)

    def draw(self):
        if not self.stretch:
            for e in self.sub_elements:
                e.draw()
            return
        if len(self.sub_elements) != 2:
            raise Exception(f'ERR: Not implemented stretched draw with more than 2 elements(amount of elements: {len(self.sub_elements)})')
        # TO-DO: Implement a better way to stretch elements
        self.sub_elements[0].draw()
        last = self.sub_elements[1]
        width = last.draw_width()
        last.set_pos(self.y, self.parent.WIDTH - width - 2)
        last.draw()