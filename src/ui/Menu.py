import ui.Buttons

class Menu:
    def __init__(self):
        self.title = ''
        self.text = ''
        self.choice_symbol = '- '
        self.buttons = []

    def add_button(self, button):
        if button not in self.buttons:
            self.buttons += [button]