import curses
import Utility

SINGLE_ELEMENT = 1
MULTIPLE_ELEMENTS = 2

def draw_borders(window):
    window.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, curses.ACS_HLINE, curses.ACS_ULCORNER, curses.ACS_URCORNER, curses.ACS_LLCORNER, curses.ACS_LRCORNER)

def message_box(window, message, choices, ypos=-1, xpos=-1, height=-1, width=-1, additional_lines=[]):
    HEIGHT, WIDTH = window.getmaxyx()
    # restrict the min and max width of message box
    if len(choices) == 0 or len(choices) > 3:
        raise Exception(f'MESSAGE_BOX ERROR: choices length can\'t be {len(choices)}')
    choice_id = 0
    done = False

    # if possible break up the messages
    if width != -1 and len(additional_lines) == 0:
        lines = Utility.str_smart_split(message, width - 6)
        if len(lines) != 1:
            message = lines[0]
            lines.pop(0)
            additional_lines = lines

    # set max min values
    max_width = WIDTH - 2

    # calculate values
    choices_len = (len(choices) + 1) * 2
    for choice in choices:
        choices_len += len(choice)
    if width == -1:
        width = max(choices_len, len(message) + 4)
        max_add_len = 0
        for add in additional_lines:
            max_add_len = max(max_add_len, len(add))
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
    draw_borders(win)

    # textpad.rectangle(win, 0, 0, height, width + 1)
    win.addstr(2, 3, message)
    win.keypad(1)
    for i in range(len(additional_lines)):
        win.addstr(3 + i, 3, additional_lines[i])
    pos = 3
    for i in range(len(choices)):
        if i == choice_id:
            win.addstr(height - 2, pos - 1, f'[{choices[i]}]')
        else:
            win.addstr(height - 2, pos, choices[i])
        pos += len(choices[i]) + 2


    while not done:
        key = win.getch()
        win.addstr(height - 2, 1, ' ' * width)
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
                win.addstr(height - 2, pos - 1, f'[{choices[i]}]')
            else:
                win.addstr(height - 2, pos, choices[i])
            pos += len(choices[i]) + 2
        if key == 10:
            done = True
        draw_borders(win)
    win.clear()
    win.refresh()
    return choices[choice_id]

def drop_down_box(options, max_display_amount, y, x, choice_type):
    HEIGHT = min(len(options), max_display_amount) + 2
    WIDTH = max([len(o) for o in options]) + 3

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
            window.addstr(i, 1, ' ' * (WIDTH - 2))
        # display
        if len(options) > max_display_amount:
            if page_n != 0:
                window.addch(1, WIDTH - 1, curses.ACS_UARROW)
            if page_n != len(options) - max_display_amount:
                window.addch(HEIGHT - 2, WIDTH - 1, curses.ACS_DARROW)
        for i in range(min(max_display_amount, len(options))):
            if i == cursor:
                window.addstr(1 + i, 1, options[i + page_n], curses.A_REVERSE)
            else:
                window.addstr(1 + i, 1, options[i + page_n])
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