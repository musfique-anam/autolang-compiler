def optimize(ir):
    out = []
    for ins in ir.instructions:
        op, args, line = ins
        # Collapse consecutive identical LED ON / LED OFF
        if out and out[-1][0] == op and op in ("LED_ON", "LED_OFF"):
            continue
        # Merge adjacent MOVE_FORWARD / MOVE_BACKWARD with same op
        if out and op in ("MOVE_FORWARD", "MOVE_BACKWARD") and out[-1][0] == op:
            prev = out.pop()
            out.append((op, (prev[1][0] + args[0],), prev[2]))
            continue
        # Merge adjacent TURN same direction
        if out and op in ("TURN_LEFT", "TURN_RIGHT") and out[-1][0] == op:
            prev = out.pop()
            out.append((op, (prev[1][0] + args[0],), prev[2]))
            continue
        # Merge adjacent WAITs
        if out and op == "WAIT" and out[-1][0] == "WAIT":
            prev = out.pop()
            out.append(("WAIT", (prev[1][0] + args[0],), prev[2]))
            continue
        out.append(ins)
    ir.instructions = out
    return ir