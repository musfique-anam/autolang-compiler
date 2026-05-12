# 🤖 AutoLang

AutoLang is a robotics-oriented Domain Specific Language (DSL) that compiles
human-readable instructions into optimized C++ code compatible with Arduino,
ESP32, STM32 and generic embedded systems.

## Features
- Full compiler pipeline: Lexer → Parser → Semantic → IR → Optimizer → C++
- Structured errors with suggestions ("Did you mean FORWARD?")
- Optimizer merges adjacent movements/turns/waits
- Pure HTML/CSS/JS web IDE with tokens, AST, IR, C++ output, robot simulation
- Python CLI compiler

## Quick Start
### CLI
```bash
python -m compiler.main examples/hello.ato > output.cpp
```

### Web
Open `website/index.html` in any modern browser. No server required.

## Project Layout
See /compiler, /website, /examples, /docs.

## License
MIT


save the output
python -m compiler.main examples/myprogram.ato > output.cpp


rm -rf compiler/__pycache__