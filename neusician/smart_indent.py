import re, io
import yaml
from .input_error import last_lines, ScorePreprocessingError

numindent_rx = r"^(\d+(?!\d*:))?([ \t]*)(.*)"

def singline(string, ini_indent=0):
    basic_indent = '  ' * ini_indent
    def _line(added_indents, space, content):
        nonlocal basic_indent
        if added_indents:
            indent = basic_indent + '  ' * int(added_indents)
        else:
            indent = basic_indent = '  ' * ini_indent + space
        return indent + content.rstrip()

    if re.search(r' ;\d', string):
        for part in re.split(r"(?<!(?<!\\)\\) ;(?=\d)", string):
            yield _line(*re.match(numindent_rx, part).groups())
    else:
        yield _line(*re.match(numindent_rx, string).groups())


def expand(string):

    look_for_loop = False
    ext = False
    loop = 1
    YAML_DOC_SEP = "\n---"

    def multiline(string):
        nonlocal look_for_loop, ext, loop
        complex_measure = singline

        for m in re.finditer(numindent_rx, string, re.MULTILINE):

            sep = ""
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
                line_split = re.split(r"\s+\|(?!\|)", m.group(0))

                if line_split[0].startswith('|'):
                    line_split[0] = line_split[0][1:]
                    complex_measure = unpack_measure
                elif complex_measure == unpack_measure:
                    preamble = line_split.pop(0)
                    yield from singline(preamble)
                    sep = YAML_DOC_SEP

                for part in line_split:
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
                    complex_measure = singline
                elif look_for_loop:
                    if string.startswith("_loop: "):
                        ext = True
                        loop = int(string.split()[1])
                        look_for_loop = False
                        continue
                    else:
                        look_for_loop = None

                parts = [m.group(0)]
                if loop and loop > 1:
                    yield f"_loop: {loop}"
                    loop = None
            else:
                parts = [m.group(0)]
            
            for part1 in parts:
                if sep: yield sep
                yield from complex_measure(part1)
                sep = YAML_DOC_SEP

    try:
        yield from multiline(string)
    except RuntimeError as e:
        raise ScorePreprocessingError from e


def unpack_measure(string):

    last_pos = 0

    def quote_nonnums(string):

        if "|" in string:
            return '"' + " | ".join(string.split("|")) + '"'

        if not re.fullmatch(r"[+-]?\d*\.?\d+([eE][+-]?\d+)?", string):
            string = '"' + string + '"'

        return string

    abbrevs = {
            "sp": "stress_pattern",
            "bpm": "beats_per_minute",
            "lsb": "lower_stress_bound",
            "usb": "upper_stress_bound",
            "ets": "elasticks_shape",
            "etp": "elasticks_pattern",
        }
    def expand_abbrevs(match):
        nonlocal last_pos
        # occurrences must be adjacent from the beginning
        # otherwise simply return matched substring
        if match.start() > last_pos:
            return match.group(0)
        else: last_pos = match.end()

        return abbrevs[ match.group("key") ] + ": " + (
                quote_nonnums(match.group("value")) + (
                    ", " if match.group("sep") else ""
                )
            )

    offset_rx = r"(\d\S*(?<=\d)|[a-z]\w*):"
    def splitter(part):
        head, *ext = re.split(r" ; " + offset_rx, part)

        if not re.match(offset_rx, part):
            head = "0: " + head

        if ext:
            formatted = []
            while ext:
                key, value, *ext = ext
                formatted.append(f"{key}: {value}\n")
            return (head, *formatted)

        else:
            return (head,)

    def meta_splicer(part):
        segments = re.split(r"(?<=\])\s([\{\w])", part, 1)
        if len(segments) == 1:
            return {}, segments[0]
        elif segments[1] == '{':
            meta = segments[0]
            articles, remainder = re.split(r"(?<=\})\s(?![^,}\]])", segments[-1], 1)
            # return meta, articles, remainder
        else:
            meta = segments[0]
            articles = ''
            remainder = segments[1]+segments[2] 

        header = {}
        if meta:
            meta = "{ " + re.sub(
                    r"(?P<key>[a-z]+):(?P<value>\d\S*?)(?P<sep>(?<=\d);(?=\D)|$)",
                    expand_abbrevs,
                    meta.strip()[1:-1]
                ) + " }"
            header['_meta'] = yaml.safe_load(meta)
        if articles:
            header['_articles'] = yaml.safe_load(articles)

        return header, remainder

    first_string, *voice_strings = string.split(" / ")
    if (m := re.match(r"((^| ;0\s*)_\w+: +[^\[\{]+?)+( ;0\s*)", first_string)):
        first_string = first_string[m.end():]
        yield from singline(m.group(0).rsplit(" ;0", 1)[0])
    if not re.match(r"\w+: ", first_string):
        header, first_string = meta_splicer(first_string)
        if header: yield yaml.dump(header).rstrip()
    voice_strings.insert(0, first_string)

    if re.match(r"\w+: ", first_string):
        unpacked = []
        for vb in voice_strings:
            ini_per_voice, *remainder_per_voice = splitter(vb)
            m = re.match(r"(\w+:)( ;0)?\s*", ini_per_voice)
            ini_per_voice = ini_per_voice[m.end():]
            voice_header, ini_per_voice = meta_splicer(ini_per_voice)
            if voice_header:
                unpacked.append(m.group(1))
                unpacked.extend(("  " + h for h in yaml.dump(voice_header).rstrip().split("\n")))
            if remainder_per_voice:
                if not voice_header: unpacked.append(m.group(1))
                unpacked.extend(singline(ini_per_voice, 1))
                for r in remainder_per_voice:
                    unpacked.extend(singline(r, 1))
            else:
                if not voice_header: unpacked.append(m.group(1))
                unpacked.extend(singline(ini_per_voice, 1))
        yield "\n".join(unpacked)
    else:
        yield from singline(("0: " if header else "") + first_string)


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
            "MORPH:\n- bla\nWS: foo | first measure",
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
        last_lines.orig_line(text)
        print(f"\n# ~~ item {i+1} ~~ #")
        # if i == 3:
        #     breakpoint()
        for line in expand(text): print(line)
