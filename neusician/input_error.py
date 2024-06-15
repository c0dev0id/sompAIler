TAIL_LENGTH = 10

class LineTracer:
    def __init__(self):
        self.unpacked = []
        self.preprocessed = []

    def orig_line(self, l):
        self.preprocessed.clear()
        self.unpacked.append(l)
        if len(self.unpacked) > TAIL_LENGTH:
            self.unpacked.pop(0)

    def unpacked_line(self, l):
        self.preprocessed.append(l)
        if len(self.preprocessed) > TAIL_LENGTH:
            self.preprocessed.pop(0)

last_lines = LineTracer()

class ScoreInputError(ValueError):
    def tail_log(self, slot='preprocessed'):
        return (
                 (last_lines.unpacked[-1] + " ==> "
                  if last_lines.unpacked and last_lines.preprocessed
                     and last_lines.unpacked[-1] != last_lines.preprocessed[-1]
                  else "")
               + "[...]\n"
               + "\n".join(getattr(last_lines, slot))
        )

class ScorePreprocessingError(ScoreInputError):
    pass

