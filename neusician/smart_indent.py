import re

def expand(string):

    basic_indent = ''

    numindent_rx = r"^(\d+(?!:))?([ \t]*)(.+)"

    def line(added_indents, space, content):
        nonlocal basic_indent
        if added_indents:
            indent = basic_indent + '  ' * int(added_indents)
        else:
            indent = basic_indent = space
        return indent + content

    def multiline(string):
        last_line_is_voice = False
        for m in re.finditer(numindent_rx, string, re.MULTILINE):

            parts = []
            if ' | ' in m.group(0):
                for part in m.group(0).split(' | '):
                    parts.append(part)
            elif not m.group(1):
                string = m.group(3)
                if string[0] in "|[" and not last_line_is_voice:
                    yield "\n---"
                else:
                    last_line_is_voice = bool(re.match(r"[a-zA-Z]\w+:\s*\#?", string))
                yield line(*re.match(numindent_rx, m.group(0)).groups())
                continue
            else:
                parts = [m.group(0)]
            
            sep = ''
            for part1 in parts:
                if sep: yield sep
                if re.search(r' ;\d', part1):
                    for part in re.split(r"(?<!(?<!\\)\\) ;(?=\d)", part1):
                        yield line(*re.match(numindent_rx, part).groups())
                else:
                    yield line(*re.match(numindent_rx, part1).groups())
                sep = "\n---"

    while len(string):
        try:
            current = string
            current, string = re.split(r'\s\|\s?(?=[\|\[])', current, 1)
        except ValueError:
            string = ''
        finally:
            yield from multiline(current)



if __name__ == '__main__':
    for line in expand(
            "name: Florian H.\n"
            "age: too old to get indentation right in the morning\n"
            "character:\n"
            "    stressed: no\n"
            "0is_friendly:\n"
            "1often: yes, kind of\n"
            "1now: without a coffee, rather mad\n"
        ): print(line)
    
    for line in expand("name: Florian H. ;0age: too old to get indentation right in the morning ;0character: ;1stressed: no ;1is_friendly: ;2often: yes, kind of ;2now: without a coffee, rather \\\\ ;2mad"): print(line)
