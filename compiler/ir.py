class IR:
    def __init__(self):
        self.instructions = []   # list of (op, args, line)
        self.tasks = {}          # name -> list of instructions

    def to_list(self):
        return [
            {"op": op, "args": list(args), "line": line}
            for op, args, line in self.instructions
        ]


def lower(ast):
    """Lower an AST into an IR object. Top-level function — must be importable."""
    ir = IR()

    # Lower all task bodies first
    for t in ast.tasks:
        ir.tasks[t.name] = [_lower_stmt(s) for s in t.body]

    # Lower main program body
    for s in ast.body:
        ir.instructions.append(_lower_stmt(s))

    # Expand RUN <task> inline
    expanded = []
    for ins in ir.instructions:
        if ins[0] == "RUN":
            expanded.extend(ir.tasks.get(ins[1][0], []))
        else:
            expanded.append(ins)
    ir.instructions = expanded
    return ir


def _lower_stmt(n):
    if n.kind == "Move":
        op = "MOVE_FORWARD" if n.direction == "FORWARD" else "MOVE_BACKWARD"
        return (op, (n.distance,), n.line)
    if n.kind == "Turn":
        op = "TURN_LEFT" if n.direction == "LEFT" else "TURN_RIGHT"
        return (op, (n.angle,), n.line)
    if n.kind == "Led":
        if n.mode == "ON":    return ("LED_ON", (), n.line)
        if n.mode == "OFF":   return ("LED_OFF", (), n.line)
        if n.mode == "BLINK": return ("LED_BLINK", (n.times,), n.line)
    if n.kind == "Buzzer":
        if n.mode == "ON":    return ("BUZZER_ON", (), n.line)
        if n.mode == "OFF":   return ("BUZZER_OFF", (), n.line)
        if n.mode == "BEEP":  return ("BUZZER_BEEP", (n.times,), n.line)
    if n.kind == "Servo":
        return ("SERVO_MOVE", (n.angle,), n.line)
    if n.kind == "Wait":  return ("WAIT", (n.seconds,), n.line)
    if n.kind == "Stop":  return ("STOP", (), n.line)
    if n.kind == "Loop":
        return ("LOOP", ([_lower_stmt(s) for s in n.body],), n.line)
    if n.kind == "Break":
        return ("BREAK", (), n.line)
    if n.kind == "Run":   return ("RUN", (n.name,), n.line)
    if n.kind == "If":
        inner = _lower_stmt(n.action)
        return ("IF", (n.condition, inner), n.line)
    raise RuntimeError(f"Cannot lower {n.kind}")