# Compiler Architecture

Source → Lexer → Parser (AST) → Semantic → IR → Optimizer → C++ Generator

- **Lexer**: splits lines, classifies KEYWORD / NUMBER / IDENT, suggests fixes.
- **Parser**: recursive-descent, builds a typed AST.
- **Semantic**: validates distances, angles, task references.
- **IR**: tuples `(op, args, line)` — e.g. `MOVE_FORWARD(10)`.
- **Optimizer**: collapses adjacent equivalent ops.
- **Generator**: prints Arduino-style C++ inside `setup()`.