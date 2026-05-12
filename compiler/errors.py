class AutoLangError(Exception):
    def __init__(self, message, line=None, hint=None):
        self.message = message
        self.line = line
        self.hint = hint
        super().__init__(self.format())

    def format(self):
        parts = []
        if self.line is not None:
            parts.append(f"Line {self.line}:")
        parts.append(self.message)
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        return " ".join(parts)


class LexError(AutoLangError): pass
class SyntaxError_(AutoLangError): pass
class SemanticError(AutoLangError): pass