import re, io

def expand(string):

    basic_indent = ''

    numindent_rx = r"^(\d+(?!\d*:))?([ \t]*)(.+)"

    def line(added_indents, space, content):
        nonlocal basic_indent
        if added_indents:
            indent = basic_indent + '  ' * int(added_indents)
        else:
            indent = basic_indent = space
        return indent + content.rstrip()

    look_for_loop = False
    ext = False
    loop = 1

    def multiline(string):
        nonlocal look_for_loop, ext, loop
        last_line_is_voice = False

        for m in re.finditer(numindent_rx, string, re.MULTILINE):

            inispace = ""
            parts = []
            partial_string = m.group(0)
            if ' ## ' in partial_string:
                partial_string = partial_string[:partial_string.index(' ## ')]
            if ' |' in partial_string:
                allpart = []
                if partial_string[0].isspace():
                    inispace = partial_string
                    partial_string = partial_string.lstrip()
                    inispace = inispace[: len(inispace) - len(partial_string)]
                else:
                    inispace = ""
                for part in re.split(r"\s+\|(?!\|)", m.group(0)):
                    if (lm := re.match(r'(?:L|\s*_loop:\s+)(\d+) ', part)):
                        if allpart: 
                            parts.append(
                                    (f"_loop: {loop} ;0 " if loop is not None else "") + ' | '.join(allpart)
                                )
                            allpart.clear()
                        loop = int(lm.group(1).strip())
                        ext = loop != 1
                        part = part[lm.end():]
                        if ext: 
                            allpart.append(part)
                            continue
                        parts.append(part)
                    elif ext:
                        allpart.append(inispace + part.lstrip())
                        inispace = ""
                        continue
                    else:
                        parts.append(part.strip())
                if allpart:
                    parts.append(
                            (f"_loop: {loop} ;0 " if loop is not None else "")
                            + ' | '.join(allpart)
                        )
                    loop = None
            elif not m.group(1):
                string = m.group(3)
                if string.startswith("---"):
                    look_for_loop = True
                elif look_for_loop:
                    if string.startswith("_loop: "):
                        ext = True
                        loop = int(string.split()[1])
                        look_for_loop = False
                        continue
                    else:
                        look_for_loop = None

                if string[0] in "|[" and not last_line_is_voice:
                    yield "\n---"
                else:
                    last_line_is_voice = bool(re.match(r"[a-zA-Z]\w+:\s*\#?", string))
                parts = [m.group(0)]
                if loop and loop > 1:
                    yield f"_loop: {loop}"
                    loop = None
            else:
                parts = [m.group(0)]
            
            sep = ""
            for part1 in parts:
                if sep: yield sep
                if re.search(r' ;\d', part1):
                    for part in re.split(r"(?<!(?<!\\)\\) ;(?=\d)", part1):
                        yield line(*re.match(numindent_rx, part).groups())
                else:
                    yield line(*re.match(numindent_rx, part1).groups())
                sep = "\n---"

    yield from multiline(string)


def unindent_from(fileobj):
    out = io.StringIO()
    current_indent = []
    initial = True
    newline = False
    for line in fileobj:
        while current_indent:
            ci = sum(current_indent)
            if line.startswith(" " * ci):
                line = line[ci:]
                break
            else:
                current_indent.pop(-1)
        if (m := re.match("( +)", line)):
            line = line[m.end():]
            current_indent.append(m.end())
        if line.startswith("---"):
            if line.rstrip() != '---':
                print("\n" + line.rstrip(), file=out)
                newline = False
            else:
                print(" | ", file=out, end="")
            initial = True
        elif line == "\n":
            newline = True
        else:
            osp = " " if re.match(r"\d", line) else ""
            if initial:
                print(line.rstrip(), file=out, end="")
                initial = newline = False
            else:
                print(f" ;{len(current_indent)}{osp}{line.rstrip()}", file=out, end="")

    return out.getvalue()


if __name__ == '__main__':
    for i, text in enumerate((
            "name: Florian H.\n"
            "age: too old to get indentation right in the morning\n"
            "character:\n"
            "    stressed: no\n"
            "0is_friendly:\n"
            "1often: yes, kind of\n"
            "1now: without a coffee, rather mad\n",
            "name: Florian H. ;0age: too old to get indentation right in the morning ;0character: ;1stressed: no ;1is_friendly: ;2often: yes, kind of ;2now: without a coffee, rather \\\\ ;2mad",
            "name: Hey, you! |L4 one | two | three | four | _loop: 1 greeting: Bye | comment: Get out of here",
            "---\n_loop: 16\nw:\n  x: bla | ne\ny: blub",
            "---\nz: whatever",
            "---\n_loop: 3\n_meta: ababab | cdcdcd | efefef || *\na: ghghgh | ijijij |L1 eins | zwei"
         )):
        print(f"\n# ~~ item {i+1} ~~ #")
        # if i == 3:
        #     breakpoint()
        for line in expand(text):
            print(line)
