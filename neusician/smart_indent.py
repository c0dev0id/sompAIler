import re

def expand(string):

    basic_indent = ''

    numindent_rx = r"^(\d+)?([ \t]*)(.+)"
    def line(added_indents, space, content):
        nonlocal basic_indent
        if added_indents:
            indent = basic_indent + '  ' * int(added_indents)
        else:
            indent = basic_indent = space
        return indent + content

    for m in re.finditer(numindent_rx, string, re.MULTILINE):

        if re.search(r' ;\d', m.group(0)):
            for part in re.split(r"(?<!(?<!\\)\\) ;(?=\d)", m.group(0)):
                yield line(*re.match(numindent_rx, part).groups())
        else:
                yield line(*m.groups())



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
