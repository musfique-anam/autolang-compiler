from .errors import SyntaxError_

class Node:
    def __init__(self, kind, **kw):
        self.kind = kind
        self.__dict__.update(kw)
    def to_dict(self):
        d = {"kind": self.kind}
        for k, v in self.__dict__.items():
            if k == "kind": continue
            if isinstance(v, Node): d[k] = v.to_dict()
            elif isinstance(v, list):
                d[k] = [x.to_dict() if isinstance(x, Node) else x for x in v]
            else: d[k] = v
        return d


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self, off=0): return self.tokens[self.pos + off]
    def eat(self): t = self.tokens[self.pos]; self.pos += 1; return t

    def expect(self, type_, value=None):
        t = self.peek()
        if t.type != type_ or (value is not None and t.value != value):
            exp = value or type_
            raise SyntaxError_(f"Expected '{exp}' but found '{t.value}'", line=t.line)
        return self.eat()

    def skip_newlines(self):
        while self.peek().type == "NEWLINE":
            self.eat()

    def parse(self):
        self.skip_newlines()
        self.expect("KEYWORD", "START")
        self.expect("NEWLINE")
        body, tasks = [], []
        while True:
            self.skip_newlines()
            t = self.peek()
            if t.type == "KEYWORD" and t.value == "END":
                break
            if t.type == "EOF":
                raise SyntaxError_("Missing END", line=t.line)
            if t.type == "KEYWORD" and t.value == "TASK":
                tasks.append(self._task())
            else:
                body.append(self._stmt())
        self.expect("KEYWORD", "END")
        return Node("Program", body=body, tasks=tasks)

    def _stmt(self):
        t = self.peek()
        if t.type != "KEYWORD":
            raise SyntaxError_(f"Unexpected '{t.value}'", line=t.line)
        handler = {
            "MOVE": self._move, "TURN": self._turn, "LED": self._led,
            "WAIT": self._wait, "IF": self._if, "STOP": self._stop,
            "RUN": self._run, "BUZZER": self._buzzer, "SERVO": self._servo,
            "LOOP": self._loop, "BREAK": self._break
        }.get(t.value)
        
        if not handler:
            raise SyntaxError_(f"Unknown command '{t.value}'", line=t.line)
        node = handler()
        if self.peek().type == "NEWLINE": self.eat()
        return node

    def _move(self):
        line = self.eat().line
        d = self.expect("KEYWORD").value
        if d not in ("FORWARD", "BACKWARD"):
            raise SyntaxError_(f"Expected FORWARD/BACKWARD, got {d}", line=line)
        n = self.expect("NUMBER").value
        return Node("Move", direction=d, distance=n, line=line)

    def _turn(self):
        line = self.eat().line
        d = self.expect("KEYWORD").value
        if d not in ("LEFT", "RIGHT"):
            raise SyntaxError_(f"Expected LEFT/RIGHT, got {d}", line=line)
        a = self.expect("NUMBER").value
        return Node("Turn", direction=d, angle=a, line=line)

    def _led(self):
        line = self.eat().line
        mode = self.expect("KEYWORD").value
        if mode == "BLINK":
            times = self.expect("NUMBER").value
            return Node("Led", mode="BLINK", times=times, line=line)
        if mode in ("ON", "OFF"):
            return Node("Led", mode=mode, line=line)
        raise SyntaxError_(f"Expected ON/OFF/BLINK, got {mode}", line=line)

    def _buzzer(self):
        line = self.eat().line
        mode = self.expect("KEYWORD").value
        if mode == "BEEP":
            times = self.expect("NUMBER").value
            return Node("Buzzer", mode="BEEP", times=times, line=line)
        if mode in ("ON", "OFF"):
            return Node("Buzzer", mode=mode, line=line)
        raise SyntaxError_(f"Expected ON/OFF/BEEP, got {mode}", line=line)

    def _servo(self):
        line = self.eat().line
        self.expect("KEYWORD", "MOVE")
        angle = self.expect("NUMBER").value
        return Node("Servo", angle=angle, line=line)

    def _wait(self):
        line = self.eat().line
        s = self.expect("NUMBER").value
        return Node("Wait", seconds=s, line=line)

    def _stop(self):
        line = self.eat().line
        return Node("Stop", line=line)

    def _loop(self):
        line = self.eat().line
        if self.peek().type == "NEWLINE": self.eat()
        body = []
        while True:
            self.skip_newlines()
            t = self.peek()
            if t.type == "KEYWORD" and t.value == "ENDLOOP":
                self.eat()
                break
            if t.type == "EOF" or (t.type == "KEYWORD" and t.value == "END"):
                raise SyntaxError_("Missing ENDLOOP", line=line)
            body.append(self._stmt())
        return Node("Loop", body=body, line=line)

    def _break(self):
        line = self.eat().line
        return Node("Break", line=line)

    def _if(self):
        line = self.eat().line
        cond_tokens = []
        while self.peek().type == "KEYWORD" and self.peek().value != "THEN":
            cond_tokens.append(self.eat().value)
        self.expect("KEYWORD", "THEN")
        action = self._stmt_inline()
        return Node("If", condition=" ".join(cond_tokens), action=action, line=line)

    def _stmt_inline(self):
        t = self.peek()
        handler = {
            "MOVE": self._move, "TURN": self._turn, "LED": self._led,
            "WAIT": self._wait, "STOP": self._stop, "RUN": self._run,
            "BUZZER": self._buzzer, "SERVO": self._servo, "BREAK": self._break
        }.get(t.value)
        
        if not handler:
            raise SyntaxError_(f"Invalid action after THEN: {t.value}", line=t.line)
        return handler()

    def _run(self):
        line = self.eat().line
        name = self.expect("IDENT").value
        return Node("Run", name=name, line=line)

    def _task(self):
        line = self.eat().line
        name = self.expect("IDENT").value
        self.expect("NEWLINE")
        body = []
        while True:
            self.skip_newlines()
            t = self.peek()
            if t.type == "KEYWORD" and t.value in ("END", "TASK"): break
            if t.type == "EOF": break
            body.append(self._stmt())
        return Node("Task", name=name, body=body, line=line)