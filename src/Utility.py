def str_smart_split(message, max_width):
    words = message.split()
    result = []
    line = words[0]
    for i in range(1, len(words)):
        word = words[i]
        t = line + ' ' + word
        print(f'{word} -- {t} -- {len(t)}')
        if len(line + ' ' + word) > max_width:
            result += [line]
            line = word
        else:
            line += ' ' + word
    result += [line]
    return result