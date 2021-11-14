from math import ceil, sqrt
import math

def pos_neg_int(n):
    if n > 0:
        return f'+{n}'
    return str(n)

def str_smart_split(message, max_width):
    words = message.split()
    result = []
    line = words[0]
    for i in range(1, len(words)):
        word = words[i]
        t = line + ' ' + word
        if len(line + ' ' + word) > max_width:
            result += [line]
            line = word
        else:
            line += ' ' + word
    result += [line]
    return result

def calc_pretty_bars(amount, max_amount, bar_length):
    if max_amount == 0:
        return ''
    times = ceil(amount * bar_length / max_amount)
    return times * '|' + (bar_length - times) * ' '

def distance(ay, ax, by, bx):
    return math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by))