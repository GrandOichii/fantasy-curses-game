class Menu:
    def __init__(self):
        self.title = ''
        self.text = ''
        self.choice_symbol = '- '
        self.buttons = []

    def add_button(self, button):
        if button not in self.buttons:
            self.buttons += [button]

class Button:
    def __init__(self, text, parent):
        self.text = text
        parent.add_button(self)
        self.leads_to = 0

    def connect_to(self, menu):
        self.leads_to = menu

class ActionButton(Button):
    def __init__(self, text, parent, action):
        super().__init__(text, parent)
        self.action = action
    
    def click(self):
        self.action()