import curses
from posixpath import dirname
import re
from math import ceil
from os import listdir
from os.path import isfile, join, splitext

SINGLE_ELEMENT = 1
MULTIPLE_ELEMENTS = 2

ACS_SOLID = '\u2588'

cc = {
    'red': curses.COLOR_RED,
    'blue': curses.COLOR_BLUE,
    'green': curses.COLOR_GREEN,
    'black': curses.COLOR_BLACK,
    'yellow': curses.COLOR_YELLOW,
    'cyan': curses.COLOR_CYAN,
    'magenta': curses.COLOR_MAGENTA,
    'white': curses.COLOR_WHITE
}
colors = {}
f_colors = set()
b_colors = set()
color_pair_nums = {}
pair_i = 0
color_regex = ''

def _add_color_combination(f_color: str, b_color: str):
    global pair_i
    pair_i += 1
    curses.init_pair(pair_i, cc[f_color], cc[b_color])
    color_pair_nums[f'{f_color}-{b_color}'] = pair_i
    f_colors.add(f_color)
    b_colors.add(b_color)

def _check_and_add(colors: str):
    if colors == 'normal': return
    if not colors in color_pair_nums:
        f_color, b_color = colors.split('-')
        _add_color_combination(f_color, b_color)
        _update_color_regex()

def _update_color_regex():
    global color_regex
    f_colors_regex = ''
    for c in cc:
        f_colors_regex += f'{c}|'
    f_colors_regex = f_colors_regex[:-1]
    b_colors_regex = ''
    for c in cc:
        b_colors_regex += f'{c}|'
    b_colors_regex = b_colors_regex[:-1]
    color_regex = f'#(({f_colors_regex})-({b_colors_regex})|normal) ([^#]+)'

# init colors
def init_colors():
    _add_color_combination('red', 'black')
    _add_color_combination('green', 'black')
    _add_color_combination('blue', 'black')

    # generate regex
    _update_color_regex()

def cct_real_str(message: str):
    result = ''
    message = '#normal ' + message
    split = re.findall(color_regex, message)
    for t in split:
        result += t[3]
    return result

def cct_len(message: str):
    return len(cct_real_str(message))

def pos_neg_int(n: int):
    if n > 0:
        return f'+{n}'
    return str(n)

def calc_pretty_bars(amount: int, max_amount: int, bar_length: int):
    if max_amount == 0:
        return ''
    times = ceil(amount * bar_length / max_amount)
    return times * '|' + (bar_length - times) * ' '

def put(window, y: int, x: int, message: str, attr: int=0):
    # format name: cct (curses color text) 
    # example method: def get_cct(self): ...
    # if message.startswith(':raw '):
    #     window.addstr(y, x, attr=0)
    #     return
    h, w = window.getmaxyx()
    message = '#normal ' + message
    split = re.findall(color_regex, message)
    for t in split:
        if t[0] == 'normal':
            window.addstr(y, x, t[3], attr)
        else:
            _check_and_add(t[0])
            window.attron(curses.color_pair(color_pair_nums[t[0]]))
            window.attron(attr)
            window.addstr(y, x, t[3])
            window.attroff(curses.color_pair(color_pair_nums[t[0]]))
            window.attroff(attr)
        x += len(t[3])

def draw_separator(window, y: int, color_pair: str='normal'):
    _check_and_add(color_pair)
    _, width = window.getmaxyx()
    flag = color_pair != 'normal'

    if flag:
        window.attron(curses.color_pair(color_pair_nums[color_pair]))
    window.addch(y, 0, curses.ACS_LTEE)
    window.addch(y, width - 1, curses.ACS_RTEE)
    for i in range(1, width - 1):
        window.addch(y, i, curses.ACS_HLINE)
    if flag:
        window.attroff(curses.color_pair(color_pair_nums[color_pair]))

# TO-DO: fix spaces
def str_smart_split(message: str, max_width: int):
    message = '#normal ' + message
    split = re.findall(color_regex, message)
    words = []
    for s in split:
        sw = s[3].split(' ')
        for ssw in sw:
            words += [[ssw, s[0]]]
    result = []
    line = f'#{words[0][1]} {words[0][0]}'
    word_line = words[0][0]
    for i in range(1, len(words)):
        word = words[i][0]
        if len(word_line + ' ' + word) > max_width:
            result += [line]
            word_line = word
            line = f'#{words[i][1]} {word}'
        else:
            if words[i][1] != words[i - 1][1]:
                line += f'#{words[i][1]}'
            line += ' ' + word
            word_line += ' ' + word
    result += [line]
    return result

def draw_borders(window, color_pair: str='normal'):
    if color_pair == 'normal':
        window.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)
    else:
        _check_and_add(color_pair)
        window.attron(curses.color_pair(color_pair_nums[color_pair]))
        window.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)
        window.attroff(curses.color_pair(color_pair_nums[color_pair]))

def drop_down_box(options: list, max_display_amount: int, y: int, x: int, choice_type: int):
    HEIGHT = min(len(options), max_display_amount) + 2
    WIDTH = max([cct_len(o) for o in options]) + 3

    window = curses.newwin(HEIGHT, WIDTH, y, x)
    window.keypad(1)

    results = set()
    indexes = [i for i in range(len(options))]
    cursor = 0
    page_n = 0
    choice = 0
    draw_borders(window)
    while True:
        # clear lines
        window.addch(1, WIDTH - 1, curses.ACS_VLINE)
        window.addch(HEIGHT - 2, WIDTH - 1, curses.ACS_VLINE)
        for i in range(1, HEIGHT - 1):
            put(window, i, 1, ' ' * (WIDTH - 2))
        # display
        if len(options) > max_display_amount:
            if page_n != 0:
                window.addch(1, WIDTH - 1, curses.ACS_UARROW)
            if page_n != len(options) - max_display_amount:
                window.addch(HEIGHT - 2, WIDTH - 1, curses.ACS_DARROW)
        for i in range(min(max_display_amount, len(options))):
            if i == cursor:
                put(window, 1 + i, 1, options[i + page_n], curses.A_REVERSE)
            else:
                put(window, 1 + i, 1, options[i + page_n])
        # key processing
        key = window.getch()
        if key == 27: # ESC
            break
        if key == 259: # UP
            choice -= 1
            cursor -= 1
            if cursor < 0:
                if len(options) > max_display_amount:
                    if page_n == 0:
                        cursor = max_display_amount - 1
                        choice = len(options) - 1
                        page_n = len(options) - max_display_amount
                    else:
                        page_n -= 1
                        cursor += 1
                else:
                    cursor = len(options) - 1
                    choice = cursor
        if key == 258: # DOWN
            choice += 1
            cursor += 1
            if len(options) > max_display_amount:
                if cursor >= max_display_amount:
                    cursor -= 1
                    page_n += 1
                    if choice == len(options):
                        choice = 0
                        cursor = 0
                        page_n = 0
            else:
                if cursor >= len(options):
                    cursor = 0
                    choice = 0
        if key == 10: # ENTER
            if choice == -1:
                break
            results.add(indexes[choice])
            if choice_type == SINGLE_ELEMENT:
                break
            options.pop(choice)
            indexes.pop(choice)
            if len(options) > max_display_amount:
                if page_n == len(options) - max_display_amount + 1:
                    page_n -= 1
                    choice -= 1
            else:
                if page_n == 1:
                    page_n = 0
                    choice -= 1
                if choice == len(options):
                    cursor -= 1
                    choice -= 1
    return list(results)

def message_box(parent, message: str, choices: list, ypos: int=-1, xpos: int=-1, height: int=-1, width: int=-1, additional_lines: list=[], border_color: str='normal'):
    window = parent.window
    HEIGHT, WIDTH = window.getmaxyx()
    # restrict the min and max width of message box
    if len(choices) == 0 or len(choices) > 3:
        raise Exception(f'MESSAGE_BOX ERROR: choices length can\'t be {len(choices)}')
    choice_id = 0
    done = False

    # if possible break up the messages
    if width != -1 and len(additional_lines) == 0:
        lines = str_smart_split(message, width - 6)
        if len(lines) != 1:
            message = lines[0]
            lines.pop(0)
            additional_lines = lines

    # set max min values
    max_width = WIDTH - 2

    # calculate values
    choices_len = (len(choices) + 1) * 2
    for choice in choices:
        choices_len += cct_len(choice)
    if width == -1:
        width = max(choices_len, cct_len(message) + 4)
        max_add_len = 0
        for add in additional_lines:
            max_add_len = max(max_add_len, cct_len(add))
        max_add_len += 4
        width = max(width, max_add_len)
        width = min(max_width, width)

    if height == -1:
        height = 6 + len(additional_lines)

    if ypos == -1:
        ypos = (HEIGHT - height) // 2
    if xpos == -1:
        xpos = (WIDTH - width) // 2
    
    # print the message box itself
    win = curses.newwin(height + 1, width + 2, ypos - 1, xpos)
    draw_borders(win, border_color)

    put(win, 2, 3, message)
    win.keypad(1)
    for i in range(len(additional_lines)):
        put(win, 3 + i, 3, additional_lines[i])
    pos = 3

    key = -1
    while not done:
        put(win, height - 2, 1, ' ' * width)
        win.refresh()
        if key == 260: # LEFT
            choice_id -= 1
            if choice_id < 0:
                choice_id = len(choices) - 1
        if key == 261: # RIGHT
            choice_id += 1
            if choice_id >= len(choices):
                choice_id = 0
        if 'Cancel' in choices and key == 27: # ESC
            win.clear()
            win.refresh()
            return 'Cancel'
        pos = 3
        for i in range(len(choices)):
            if i == choice_id:
                put(win, height - 2, pos - 1, f'[{choices[i]}')
                win.addstr(height - 2, pos + cct_len(choices[i]), ']')
            else:
                put(win, height - 2, pos, choices[i])
            pos += cct_len(choices[i]) + 2
        key = win.getch()
        if key == 10:
            done = True
        draw_borders(win)
    win.clear()
    win.refresh()
    return choices[choice_id]

def choose_file(parent, title: str, starting_directory: str='.'):
    w_height = parent.HEIGHT // 8 * 5
    w_width = parent.WIDTH // 8 * 5
    w_y = (parent.HEIGHT - w_height) // 2
    w_x = (parent.WIDTH - w_width) // 2
    window = curses.newwin(w_height, w_width, w_y, w_x)
    window.keypad(1)

    path = starting_directory
    max_display_amount = w_height - 3
    choice = 0
    cursor = 0
    page_n = 0
    while True:
        # get dir info
        paths = ['..']
        p = listdir(path)
        pfolders = []
        pfiles = []
        for pp in p:
            if isfile(f'{path}/{pp}'):
                pfiles += [pp]
            else:
                pfolders += [pp]
        paths += pfolders
        paths += pfiles

        # display
        draw_borders(window)
        window.addstr(0, 0, ACS_SOLID)
        window.addstr(0, 1, title)
        window.addch(0, 0, curses.ACS_BOARD)
        for i in range(min(max_display_amount, len(paths))):
            attr = curses.A_REVERSE if i == cursor else 0
            if not isfile(f'{path}/{paths[i + page_n]}'):
                put(window, 2 + i, 2, f'#cyan-black {paths[i + page_n]}', attr)
            else:
                window.addstr(2 + i, 2, paths[i + page_n], attr)
        # key handling
        key = window.getch()
        if key == 10: # ENTER
            if paths[choice] == '..':
                path = dirname(path)
                choice = 0
                cursor = 0
                page_n = 0
            else:
                full_path = f'{path}/{paths[choice]}'
                if isfile(full_path):
                    try:
                        open(full_path, 'r')
                        return re.sub('/+', '/', full_path)
                    except PermissionError:
                        message_box(parent, 'Premission denied', ['Ok'])
                        continue
                try:
                    listdir(f'{path}/{paths[choice]}')
                    path += f'/{paths[choice]}'
                    choice = 0
                    cursor = 0
                    page_n = 0
                except PermissionError:
                    message_box(parent, 'Premission denied', ['Ok'])
        if key == 259: # UP
            choice -= 1
            cursor -= 1
            if cursor < 0:
                if len(paths) > max_display_amount:
                    if page_n == 0:
                        cursor = max_display_amount - 1
                        choice = len(paths) - 1
                        page_n = len(paths) - max_display_amount
                    else:
                        page_n -= 1
                        cursor += 1
                else:
                    cursor = len(paths) - 1
                    choice = cursor
        if key == 258: # DOWN
            choice += 1
            cursor += 1
            if len(paths) > max_display_amount:
                if cursor >= max_display_amount:
                    cursor -= 1
                    page_n += 1
                    if choice == len(paths):
                        choice = 0
                        cursor = 0
                        page_n = 0
            else:
                if cursor >= len(paths):
                    cursor = 0
                    choice = 0

        # clear screen
        window.clear()

def show_controls_window(parent, controls: dict):
    # TO-DO: Add scrolling
    window = parent.window
    HEIGHT, WIDTH = window.getmaxyx()
    controls_window_height = HEIGHT * 1 // 3
    controls_window_width = WIDTH * 1 // 3
    controls_window_y = (HEIGHT - controls_window_height) // 2
    controls_window_x = (WIDTH - controls_window_width) // 2
    controls_window = curses.newwin(controls_window_height, controls_window_width, controls_window_y, controls_window_x)
    controls_window.keypad(1)

    # initial draw
    draw_borders(controls_window)
    put(controls_window, 0, 1, '#green-black Controls')

    keys = list(controls.keys())
    descriptions = list(controls.values())
    description_offset = 1

    while True:
        # clear screen
        for i in range(1, controls_window_height - 1):
            controls_window.addstr(i, 1, ' ' * (controls_window_width - 2))
        # display controls
        for i in range(len(keys)):
            put(controls_window, 1 + i, 2, f'{descriptions[i]}:')
            k_len = len(keys[i])
            put(controls_window, 1 + i, controls_window_width - k_len - description_offset - 1, f'#green-black {keys[i]}')
            # draw placeholder
            # put(controls_window, 1 + i, len(keys[i]) + 1, '_' * (controls_window_width - len(keys[i]) - len(descriptions[i]) - 2))

        # key handling
        key = controls_window.getch()
        if key == 27 or key == 10 or key == 63: # ESC/ENTER/?
            break
