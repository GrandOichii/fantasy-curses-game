from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QShortcut, QSpinBox, QWidget, qApp

import sys

# from PyQt5.sip import delete

def window():
    app = QApplication([])
    win = MainAppWindow()
    win.show()
    sys.exit(app.exec_())

class TileLabel(QLabel):
    def __init__(self, parent, tile_info, map_y, map_x, right_click_action):
        QLabel.__init__(self, parent)
        self.tile_info = tile_info
        self.border_color = 'black'
        self.border_style = f'border: 3px solid '
        self.background_color_style = ';\nbackground-color: '
        color = parent.tiles_dict[tile_info.split()[0]]['color']
        self.color = color
        self.setStyleSheet(f'{self.border_style}{self.border_color}{self.background_color_style}{self.color}')
        self.right_click_action = right_click_action
        self.map_y = map_y
        self.map_x = map_x
        self.is_hidden = False
        self.hidden_tile_info = ''

    def set_border_color(self, color):
        self.border_color = color
        self.setStyleSheet(f'{self.border_style}{self.border_color}{self.background_color_style}{self.color}')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            tile = self.parent().tile
            if self.tile_info == tile:
                return
            self.tile_info = tile
            tiles_dict = self.parent().tiles_dict
            color = tiles_dict[tile]['color']
            self.color = color
            self.setStyleSheet(f'{self.border_style}{self.border_color}{self.background_color_style}{self.color}')
        elif self.right_click_action:
            self.right_click_action(self, event)

class TileColorChoiceLabel(QLabel):
    def __init__(self, color, text, action, parent=None):
        QLabel.__init__(self, parent)
        self.color = color
        self.setToolTip(text)
        self.action = action
        self.setFixedHeight(16)
        self.setFixedWidth(16)
        self.setStyleSheet(f'border: 1px solid black;\nbackground-color: {color}')

    def mousePressEvent(self, event):
        self.action()

class MainAppWindow(QMainWindow):
    def __init__(self):
        super(QMainWindow, self).__init__()

        self.loaded_file_path = ''

        self.tile_height = 32
        self.tile_width = 32

        self.tile = 'wall'

        self.labels = []

        self.tiles_dict = dict()
        self.tiles_dict['wall'] = {
            'color': 'gray', 
            'char': '#', 
            'action': self.set_tile_to_wall_action
        }
        self.tiles_dict['floor'] = {
            'color': 'white', 
            'char': ' ', 
            'action': self.set_tile_to_floor_action
        }
        self.tiles_dict['door'] = {
            'color': 'brown', 
            'char': 'D', 
            'action': self.set_tile_to_door_action
        }
        self.tiles_dict['torch'] = {
            'color': 'orange', 
            'char': 'I', 
            'action': self.set_tile_to_torch_action
        }
        self.tiles_dict['pressure_plate'] = {
            'color': 'red', 
            'char': '_', 
            'action': self.set_tile_to_pressure_plate_action
        }
        self.tiles_dict['script_tile'] = {
            'color': 'blue',
            'char': '|',
            'action': self.set_tile_to_script_action
        }

        self.setGeometry(0, 0, 400, 620)
        self.setWindowTitle('Map maker')
        self.initUI()
        self.show()

    def initUI(self):
        new_map_action = QAction('New map', self)
        new_map_action.setShortcut('Ctrl+N')
        new_map_action.setStatusTip('Create new map')
        new_map_action.triggered.connect(self.new_map_action_triggered)

        load_map_action = QAction('Load map', self)
        load_map_action.setShortcut('Ctrl+O')
        load_map_action.setStatusTip('Load an existing map')
        load_map_action.triggered.connect(self.load_map_action_triggered)

        save_map_action = QAction('Save', self)
        save_map_action.setShortcut('Ctrl+S')
        save_map_action.setStatusTip('Save map')
        save_map_action.triggered.connect(self.save_map_action_triggered)

        save_map_as_action = QAction('Save as', self)
        save_map_as_action.setShortcut('Ctrl+Shift+S')
        save_map_as_action.setStatusTip('Save map as')
        save_map_as_action.triggered.connect(self.save_map_as_action_triggered)

        edit_scripts_act = QAction('Edit scripts', self)
        edit_scripts_act.setStatusTip('Edit scripts')
        edit_scripts_act.triggered.connect(self.edit_scripts_action_triggered)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(new_map_action)
        file_menu.addAction(load_map_action)
        file_menu.addSeparator()
        file_menu.addAction(save_map_action)
        file_menu.addAction(save_map_as_action)

        edit_menu = menubar.addMenu('&Edit')
        edit_menu.addAction(edit_scripts_act)

        quit_shortcut = QShortcut(QKeySequence('Ctrl+Q'), self)
        quit_shortcut.activated.connect(qApp.quit)

        change_to_wall_shortcut = QShortcut(QKeySequence('Ctrl+W'), self)
        change_to_wall_shortcut.activated.connect(self.set_tile_to_wall_action)

        change_to_floor_shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        change_to_floor_shortcut.activated.connect(self.set_tile_to_floor_action)

        change_to_door_shortcut = QShortcut(QKeySequence('Ctrl+D'), self)
        change_to_door_shortcut.activated.connect(self.set_tile_to_door_action)

        change_to_torch_shortcut = QShortcut(QKeySequence('Ctrl+T'), self)
        change_to_torch_shortcut.activated.connect(self.set_tile_to_torch_action)

        self.tiles_color_choice = QWidget(self)
        tiles_color_choice_layout = QHBoxLayout()
        i = -1
        for key in self.tiles_dict:
            i += 1
            tile = TileColorChoiceLabel(self.tiles_dict[key]['color'], key, self.tiles_dict[key]['action'])
            tiles_color_choice_layout.addWidget(tile, i)
        self.tiles_color_choice.setLayout(tiles_color_choice_layout)
        
        self.visible_range_label = QLabel(self)
        self.visible_range_label.setText('visible_range=')
        self.visible_range_label.setFixedWidth(100)
        self.visible_range_label.setFixedHeight(30)

        self.visible_range_spin_box = QSpinBox(self)
        self.visible_range_spin_box.setMinimum(0)
        self.visible_range_spin_box.setFixedWidth(50)
        
        self.load(['##########', '#        #', '#        #', '#        #', '#        #', '#        #', '#        #', '#        #', '#        #', '##########'], ['visible_range=10'], [], '')
        
    def new_map_action_triggered(self):
        if QMessageBox.question(self, 'Map maker', 'Ensaved changes will be discarded. Continue?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            height, ok = QInputDialog.getInt(self, 'Map maker', 'Enter the map height', 10)
            if height and ok:
                width, ok = QInputDialog.getInt(self, 'Map maker', 'Enter the map width', 10)
                if width and ok:
                    self.loaded_file_path = ''
                    layout = []
                    layout += ['#' * width]
                    for _ in range(height - 2):
                        layout += ['#' + ' ' * (width - 2) + '#']
                    layout += ['#' * width]
                    map_info = ['visible_range=10']
                    tiles_info = []
                    scripts_info = ''
                    self.load(layout, map_info, tiles_info, scripts_info)

    def load_map_action_triggered(self):
        if QMessageBox.question(self, 'Map maker', 'Ensaved changes will be discarded. Continue?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            path = QFileDialog.getOpenFileName(self, 'Open', '', 'Map files(*.map)')[0]
            if path:
                text = open(path, 'r').read()
                split = text.split('\n---\n')
                layout = []
                for line in split[0].split('\n'):
                    layout += [line]
                map_info = split[1].split('\n')
                tiles_info = split[2].split('\n')
                scripts_info = split[3]
                self.loaded_file_path = path
                self.load(layout, map_info, tiles_info, scripts_info)

    def save_map_as_action_triggered(self):
        path = QFileDialog.getSaveFileName(self, 'Save as', '', 'Map files(*.map)')[0]
        if path:
            self.loaded_file_path = path
            self.save_map_action_triggered()

    def save_map_action_triggered(self):
        if self.loaded_file_path == '':
            self.save_map_as_action_triggered()
            return

        result_layout = []
        result_map_data = dict()
        result_tile_data = []
        result_map_data['visible_range'] = self.visible_range_spin_box.value()
        char_int = 64
        hidden_floors_chars = dict()
        for i in range(self.map_height):
            result_layout += ['']
            for j in range(self.map_width):
                tile = self.labels[i][j]
                tile_info = tile.tile_info.split(' ')
                tile_name = tile_info[0]
                # if torch visibility is not set
                if len(tile_info) == 1 and tile_info[0] == 'torch':
                    tile_info += ['5']
                
                if tile.is_hidden:
                    if tile_name == 'floor':
                        if tile.hidden_tile_info == '':
                            self.showMB('Hidden tile at y:{tile.map_y}, x:{tile.map_x} doesn\'t catch a signal!', 'Error')
                            return
                        if not tile.hidden_tile_info in hidden_floors_chars.keys():
                            char_int += 1
                            hidden_floors_chars[tile.hidden_tile_info] = f'{chr(char_int)} # hidden_tile {tile.hidden_tile_info}'
                            result_tile_data += [hidden_floors_chars[tile.hidden_tile_info]]
                        result_layout[i] += hidden_floors_chars[tile.hidden_tile_info][0]
                        continue
                    if tile_name == 'script_tile':
                        char_int += 1
                        result_layout[i] += chr(char_int)
                        if tile.hidden_tile_info == '':
                            self.showMB('Hidden tile at y:{tile.map_y}, x:{tile.map_x} doesn\'t catch a signal!', 'Error')
                            return
                        line = f'{chr(char_int)} # hidden_tile {tile.hidden_tile_info}'
                        line += f' {tile_info[1]} {tile_info[0]} {tile_info[2]} {tile_info[3]}'
                        result_tile_data += [line]
                        continue
                    char_int += 1
                    result_layout[i] += chr(char_int)
                    if tile.hidden_tile_info == '':
                        self.showMB('Hidden tile at y:{tile.map_y}, x:{tile.map_x} doesn\'t catch a signal!', 'Error')
                        return
                    line = f'{chr(char_int)} # hidden_tile {tile.hidden_tile_info}'
                    if len(tile_info) != 1:
                        c = self.tiles_dict[tile_info[0]]['char']
                        args = ' '.join(tile_info[1:len(tile_info)])
                        line += f' {c} {tile_info[0]} {args}'
                    result_tile_data += [line]
                    continue
                if tile_name == 'wall':
                    result_layout[i] += '#'
                    continue
                if tile_name == 'floor':
                    if len(tile_info) == 2 and tile_info[1] == 'spawn_point':
                        result_layout[i] += '@'
                    else:
                        result_layout[i] += ' '
                    continue
                if tile_name == 'torch':
                    char_int += 1
                    result_layout[i] += chr(char_int)
                    if len(tile_info) != 2:
                        raise Exception(f'ERR: torch at y:{tile.map_y}, x:{tile.map_x} doesn\'t have visible range')
                    visible_range = int(tile_info[1])
                    result_tile_data += [f'{chr(char_int)} I torch {visible_range}']
                    continue
                if tile_name == 'door':
                    char_int += 1
                    result_layout[i] += chr(char_int)
                    if len(tile_info) != 3:
                        self.showMB(f'Door at y:{tile.map_y}, x:{tile.map_x} doesn\'t lead anywhere!', 'Error')
                        return
                    result_tile_data += [f'{chr(char_int)} D door {tile_info[1]} {tile_info[2]}']
                    continue
                if tile_name == 'pressure_plate':
                    char_int += 1
                    result_layout[i] += chr(char_int)
                    if len(tile_info) != 2:
                        self.showMB(f'Pressure plate at y:{tile.map_y}, x:{tile.map_x} doesn\'t emit a signal!', 'Error')
                        return
                    result_tile_data += [f'{chr(char_int)} _ pressure_plate {tile_info[1]}']
                if tile_name == 'script_tile':
                    char_int += 1
                    result_layout[i] += chr(char_int)
                    if len(tile_info) == 1:
                        self.showMB(f'Script tile at y: {tile.map_y}, x: {tile.map_x} doesn\'t have a script!', 'Error')
                        return
                    result_tile_data += [f'{chr(char_int)} {tile_info[1]} script_tile {tile_info[2]} {tile_info[3]}']
        result = ''
        for line in result_layout:
            result += f'{line}\n'
        result += '---\n'
        for key in result_map_data:
            result += f'{key}={result_map_data[key]}\n'
        result += '---\n'
        for line in result_tile_data:
            result += f'{line}\n'
        result += '---\n'

        result += self.get_scripts_text()

        open(self.loaded_file_path, 'w').write(result)
        self.showMB('Saved!', 'Map maker')

    def get_scripts_text(self):
        result = ''
        script_names = list(self.scripts.keys())
        scripts = list(self.scripts.values())
        for i in range(len(script_names)):
            result += f'{script_names[i]}:\n{scripts[i]}'
            if i != len(script_names) - 1:
                result += '\n\n'
        return result

    def edit_scripts_action_triggered(self):
       value = self.get_scripts_text()
       result, ok = QInputDialog.getMultiLineText(self, 'Script editor', 'Edit the scripts', value)
       if ok and result:
           self.set_scripts(result)

    def set_scripts(self, text):
        self.scripts = dict()

        if len(text) == 0:
            return

        for script in text.split('\n\n'):
            lines = script.split('\n')
            script_name = lines[0][:-1]
            self.scripts[script_name] = '\n'.join(lines[1:])

    def load(self, layout, map_info, tiles_info, scripts_info):
        self.set_scripts(scripts_info)

        if len(self.labels) != 0:
            for i in range(self.map_height):
                for j in range(self.map_width):
                    self.labels[i][j].hide()
        # map layout
        self.map_height = len(layout)
        self.map_width = len(layout[0])

        tiles_data = dict()
        for line in tiles_info:
            if line == '':
                continue
            s = line.split()
            key = s[0]
            s.pop(0)
            char = s[0]
            s.pop(0)
            m = dict()
            if s[0] == 'hidden_tile':
                m['is_hidden'] = True
                m['hidden_tile_info'] = s[1]
                if len(s) == 2: # is floor
                    m['tile_info'] = 'floor'
                    tiles_data[key] = m
                    continue
                s = s[3: len(s)]
            if s[0] == 'script_tile':
                m['tile_info'] = f'script_tile {char} {s[1]} {s[2]}'               
            else:
                m['tile_info'] = ' '.join(s)
            tiles_data[key] = m

        self.labels = []
        for i in range(self.map_height):
            self.labels += [[]]
            for j in range(self.map_width):
                tile_info = 'ERR'
                flag = layout[i][j] in tiles_data.keys()
                if layout[i][j] == '#':
                    tile_info = 'wall'
                if layout[i][j] == '@':
                    tile_info = 'floor spawn_point'
                if layout[i][j] == ' ':
                    tile_info = 'floor'  
                if flag:
                    tile_info = tiles_data[layout[i][j]]['tile_info']
                label = TileLabel(self, tile_info, i, j, self.right_click_action)
                if flag:
                    d = tiles_data[layout[i][j]]
                    if 'is_hidden' in d:
                        label.is_hidden = True
                        label.hidden_tile_info = d['hidden_tile_info']
                        label.set_border_color('green')

                label.setGeometry(1 + j * self.tile_width, 21 + i * self.tile_height, self.tile_width, self.tile_height)
                self.labels[i] += [label]
                label.show()                
                
        self.setFixedWidth(self.tile_width * self.map_width + 200)
        self.setFixedHeight(self.tile_height * self.map_height + 23)
                
        # map data
        for line in map_info:
            s = line.split('=')
            if s[0] == 'visible_range':
                self.visible_range_spin_box.setValue(int(s[1]))

        # move the ui
        self.tiles_color_choice.move(self.tile_width * self.map_width + 2, 21)
        self.visible_range_label.move(self.tile_width * self.map_width + 14, 61)
        self.visible_range_spin_box.move(self.tile_width * self.map_width + 105, 61)

    def right_click_action(self, tile, event):
        tile_name = tile.tile_info.split()[0]
        context_menu = QMenu(self)
        make_visible_act = None
        set_signal_act = None
        make_hidden_tile_act = None
        make_spawn_point_act = None
        delete_spawn_point_act = None
        set_visible_range = None
        set_door_signal = None
        set_pressure_plate_signal_act = None
        set_script_act = None
        if tile.is_hidden:
            make_visible_act = context_menu.addAction('Make visible')
            set_signal_act = context_menu.addAction('Set hidden signal')
        else:
            make_hidden_tile_act = context_menu.addAction('Make a hidden tile')
        context_menu.addSeparator()
        if tile_name == 'floor' and not tile.is_hidden:
            if len(tile.tile_info.split()) == 1:
                make_spawn_point_act = context_menu.addAction('Mark as spawn point')
            else:
                delete_spawn_point_act = context_menu.addAction('Delete spawn point')
        if tile_name == 'torch':
            set_visible_range = context_menu.addAction('Set visible range')
        if tile_name == 'door':
            set_door_signal = context_menu.addAction('Set door signal')
        if tile_name == 'pressure_plate':
            set_pressure_plate_signal_act = context_menu.addAction('Set signal')
        if tile_name == 'script_tile':
            set_script_act = context_menu.addAction('Set script')
        
        action = context_menu.exec_(self.mapToGlobal(tile.pos() + event.pos()))
        if action == None:
            return
        if action == set_visible_range:
            value = 0
            tis = tile.tile_info.split()
            if len(tis) == 2:
                value = int(tis[1])
            result, ok = QInputDialog.getInt(self, 'Visible range', 'Enter range:', value)
            if ok and result:
                tile.tile_info = f'{tis[0]} {result}'
        if action == make_hidden_tile_act or action == set_signal_act:
            value = ''
            if len(tile.hidden_tile_info) != 0:
                value = tile.hidden_tile_info
            result, ok = QInputDialog.getText(self, 'Hidden tile signal', 'Enter the signal', text=value)
            if ok and result:
                tile.is_hidden = True
                tile.hidden_tile_info = result
                tile.set_border_color('green')
        if action == make_visible_act:
            tile.is_hidden = False
            tile.hidden_tile_info = ''
            tile.set_border_color('black')
        if action == make_spawn_point_act:
            for i in range(self.map_height):
                for j in range(self.map_width):
                    label = self.labels[i][j]
                    s = self.labels[i][j].tile_info.split()
                    if len(s) == 2 and s[0] == 'floor' and s[1] == 'spawn_point':
                        answer = QMessageBox.question(self, 'Map maker', f'Spawn is already set at y:{label.map_y}, x:{label.map_x}. Replace?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if answer == QMessageBox.Yes:
                            tile.tile_info += ' spawn_point'
                            label.tile_info = label.tile_info.split()[0]
                            return
                        else:
                            return
            tile.tile_info += ' spawn_point'
        if action == delete_spawn_point_act:
            tile.tile_info = tile_name
        if action == set_door_signal:
            value1 = ''
            value2 = ''
            tis = tile.tile_info.split()
            if len(tis) == 3:
                value1 = tis[1]
                value2 = tis[2]
            result1, ok = QInputDialog.getText(self, 'Door signal', 'Enter the map destination', text=value1)
            if ok and result1:
                result2, ok = QInputDialog.getText(self, 'Dor signal', 'Enter the door signal', text=value2)
                if ok and result2:
                    tile.tile_info = f'{tis[0]} {result1} {result2}'
        if action == set_pressure_plate_signal_act:
            value = ''
            tis = tile.tile_info.split()
            if len(tis) == 2:
                value = tis[1]
            result, ok = QInputDialog.getText(self, 'Pressure plate signal', 'Enter the signal', text=value)
            if ok and result:
                tile.tile_info = f'{tis[0]} {result}'
        if action == set_script_act:
            real_tile_name = ''
            tile_char = ''
            script = ''
            tis = tile.tile_info.split()
            if len(tis) != 1:
                tile_char = tis[1]
                real_tile_name = tis[2]
                script_name = tis[3]
            result, ok = QInputDialog.getText(self, 'Script tile name', 'Enter real name of tile', text=real_tile_name)
            if result and ok:
                real_tile_name = result
                result, ok = QInputDialog.getText(self, 'Script tile char', 'Enter the character of tile', text=tile_char)
                if result and ok:
                    tile_char = result[0]
                    script_name = f'{real_tile_name}_script'
                    script_text = ''
                    if script_name in self.scripts.keys():
                        script_text = self.scripts[script_name]
                    result, ok = QInputDialog.getMultiLineText(self, 'Script tile script', 'Enter the script', text=script_text)
                    if ok and result:
                        script = result
                        tile.tile_info = f'{tis[0]} {tile_char} {real_tile_name} {script_name}'
                        self.scripts[script_name] = script

    @pyqtSlot()
    def set_tile_to_wall_action(self):
        self.tile = 'wall'

    @pyqtSlot()
    def set_tile_to_floor_action(self):
        self.tile = 'floor'

    @pyqtSlot()
    def set_tile_to_torch_action(self):
        self.tile = 'torch'

    @pyqtSlot()
    def set_tile_to_door_action(self):
        self.tile = 'door'

    @pyqtSlot()
    def set_tile_to_script_action(self):
        self.tile = 'script_tile'

    @pyqtSlot()
    def set_tile_to_pressure_plate_action(self):
        self.tile = 'pressure_plate'

    def showMB(self, text, title):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

if __name__ == '__main__':
    window()