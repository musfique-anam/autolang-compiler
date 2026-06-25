from .errors import LexError

KEYWORDS = {
    "START", "END", "MOVE", "TURN", "LED", "WAIT", "IF", "THEN",
    "STOP", "RUN", "TASK", "FORWARD", "BACKWARD", "LEFT", "RIGHT",
    "ON", "OFF", "BLINK", "OBSTACLE", "DETECT", "SENSOR",
    "BUZZER", "BEEP", "SERVO", "LOOP", "ENDLOOP", "BREAK"
}

def _suggest(word):
    best = None
    best_d = 99
    for k in KEYWORDS:
        d = _edit(word.upper(), k)
        if d < best_d:
            best_d, best = d, k
    return best if best_d <= 2 else None

def _edit(a, b):
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(cur[-1] + 1, prev[j] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class Token:
    __slots__ = ("type", "value", "line")
    def __init__(self, type_, value, line):
        self.type, self.value, self.line = type_, value, line
    def __repr__(self):
        return f"<{self.type}:{self.value}@{self.line}>"
    def to_dict(self):
        return {"type": self.type, "value": self.value, "line": self.line}


def tokenize(source: str):
    tokens = []
    for lineno, raw in enumerate(source.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        for word in line.split():
            up = word.upper()
            if up in KEYWORDS:
                tokens.append(Token("KEYWORD", up, lineno))
            elif _is_int(word):
                tokens.append(Token("NUMBER", int(word), lineno))
            elif _is_ident(word):
                tokens.append(Token("IDENT", word, lineno))
            else:
                hint = _suggest(word)
                raise LexError(f"Unexpected token '{word}'", line=lineno,
                               hint=f"Did you mean '{hint}'?" if hint else None)
        tokens.append(Token("NEWLINE", "\\n", lineno))
    tokens.append(Token("EOF", None, lineno if tokens else 1))
    return tokens


def _is_int(s):
    try: int(s); return True
    except: return False

def _is_ident(s):
    return s and (s[0].isalpha() or s[0] == "_") and all(c.isalnum() or c == "_" for c in s)