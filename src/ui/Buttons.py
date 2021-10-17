class Button:
    def __init__(self, text: str, parent):
        self.text = text
        parent.add_button(self)
        self.leads_to = 0

    def connect_to(self, menu):
        self.leads_to = menu

class ActionButton(Button):
    def __init__(self, text: str, parent, action):
        super().__init__(text, parent)
        self.action = action
    
    def click(self):
        self.action()