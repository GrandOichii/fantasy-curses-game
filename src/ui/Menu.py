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

    def remove_button_with_name(self, name):
        for button in self.buttons:
            if button.name == name:
                self.buttons.remove(button)
                return
        raise Exception(f'ERR: No button with name {name}, could not remove')