# AutoLang Syntax

Every program is wrapped between START and END. One command per line.
Keywords are case-insensitive; uppercase is recommended.

## Commands
| Command | Example |
|---|---|
| Move | `MOVE FORWARD 10`, `MOVE BACKWARD 5` |
| Turn | `TURN LEFT 90`, `TURN RIGHT 45` |
| LED  | `LED ON`, `LED OFF`, `LED BLINK 3` |
| Wait | `WAIT 2` |
| Conditional | `IF OBSTACLE THEN STOP` |
| Task | `TASK scan` … `RUN scan` |