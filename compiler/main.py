# compiler/main.py
# ─────────────────────────────────────────────────────────────
#  AutoLang Compiler — CLI entrypoint
#
#  Pipeline:
#     Lexer → Parser → Semantic → IR → Optimizer → C++ Generator
#
#  Each compile produces its OWN sub-folder inside ./output/
#     output/
#     ├── build_log.txt
#     ├── 001_hello/
#     │   ├── hello.cpp
#     │   ├── hello.tokens.txt
#     │   ├── hello.ast.json
#     │   ├── hello.ir.txt
#     │   └── meta.txt
#     └── 002_patrol/
#         └── ...
# ─────────────────────────────────────────────────────────────

import sys
import os
import json
import datetime

from .lexer import tokenize
from .parser import Parser
from .semantic import Semantic
from .ir import lower
from .optimizer import optimize
from .generator import generate
from .errors import AutoLangError


# ---------- Configuration ----------
ALLOWED_EXT = ".ato"
BUILD_DIR   = "output"
LOG_FILE    = os.path.join(BUILD_DIR, "build_log.txt")


# =============================================================
#  Core compile routine
# =============================================================
def compile_source(src: str) -> dict:
    """Run the full AutoLang pipeline on a source string.

    Returns a dict with tokens, ast, ir, cpp, and any errors.
    """
    result = {
        "ok": True,
        "tokens": [],
        "ast": None,
        "ir": [],
        "cpp": "",
        "errors": [],
    }
    try:
        toks = tokenize(src)
        result["tokens"] = [t.to_dict() for t in toks]

        ast = Parser(toks).parse()
        result["ast"] = ast.to_dict()

        Semantic(ast).analyze()

        ir = optimize(lower(ast))
        result["ir"] = ir.to_list()

        result["cpp"] = generate(ir)

    except AutoLangError as e:
        result["ok"] = False
        result["errors"].append(str(e))
    except Exception as e:
        # Catch-all so the CLI never crashes on unexpected bugs
        result["ok"] = False
        result["errors"].append(f"Internal error: {e}")

    return result


# =============================================================
#  Output helpers
# =============================================================
def _next_rank() -> str:
    """Return next 3-digit rank (e.g. '001') based on folders in output/."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    existing = [
        name for name in os.listdir(BUILD_DIR)
        if len(name) >= 3 and name[:3].isdigit()
        and os.path.isdir(os.path.join(BUILD_DIR, name))
    ]
    ranks = [int(name[:3]) for name in existing] if existing else [0]
    return f"{max(ranks) + 1:03d}"


def _write_outputs(src_path: str, r: dict):
    """Each compile gets its OWN sub-folder inside output/."""
    os.makedirs(BUILD_DIR, exist_ok=True)

    rank      = _next_rank()
    stamp     = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = os.path.splitext(os.path.basename(src_path))[0]

    # Per-run sub-folder, e.g. output/001_hello/
    run_dir = os.path.join(BUILD_DIR, f"{rank}_{base_name}")
    os.makedirs(run_dir, exist_ok=True)

    paths = {
        "cpp":    os.path.join(run_dir, f"{base_name}.cpp"),
        "tokens": os.path.join(run_dir, f"{base_name}.tokens.txt"),
        "ast":    os.path.join(run_dir, f"{base_name}.ast.json"),
        "ir":     os.path.join(run_dir, f"{base_name}.ir.txt"),
        "meta":   os.path.join(run_dir, "meta.txt"),
    }

    # 1) Generated C++
    with open(paths["cpp"], "w") as f:
        f.write(r["cpp"])

    # 2) Token stream (human-readable)
    with open(paths["tokens"], "w") as f:
        for t in r["tokens"]:
            f.write(f"{t['type']:<8} {str(t['value']):<15} line={t['line']}\n")

    # 3) AST (pretty JSON)
    with open(paths["ast"], "w") as f:
        json.dump(r["ast"], f, indent=2)

    # 4) IR listing
    with open(paths["ir"], "w") as f:
        for ins in r["ir"]:
            args = ", ".join(map(str, ins["args"]))
            f.write(f"{ins['op']}({args})   # line {ins['line']}\n")

    # 5) Metadata card
    with open(paths["meta"], "w") as f:
        f.write("AutoLang compile report\n")
        f.write("-----------------------\n")
        f.write(f"Rank      : {rank}\n")
        f.write(f"Source    : {src_path}\n")
        f.write(f"Timestamp : {stamp}\n")
        f.write(f"Tokens    : {len(r['tokens'])}\n")
        f.write(f"IR ops    : {len(r['ir'])}\n")

    # 6) Global build log (append)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{rank}] {stamp}  src={src_path}  ->  {run_dir}\n")

    return rank, run_dir, paths


# =============================================================
#  CLI
# =============================================================
def _print_usage():
    print("AutoLang Compiler")
    print("-----------------")
    print("Usage:")
    print(f"  python -m compiler.main <file{ALLOWED_EXT}> [file2{ALLOWED_EXT} ...]")
    print()
    print("Options:")
    print("  -h, --help     Show this help message")
    print()
    print("Examples:")
    print(f"  python -m compiler.main examples/hello{ALLOWED_EXT}")
    print(f"  python -m compiler.main examples/hello{ALLOWED_EXT} examples/patrol{ALLOWED_EXT}")
    print()
    print(f"Outputs are written to ./{BUILD_DIR}/ with one sub-folder per compile.")


def main():
    # Handle help / empty args
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _print_usage()
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    src_files = sys.argv[1:]
    print(f"🛠  AutoLang — Compiling {len(src_files)} file(s) → ./{BUILD_DIR}/\n")

    success = 0
    failed  = 0

    for src_path in src_files:
        # Extension check
        if not src_path.endswith(ALLOWED_EXT):
            print(f"⚠  Skipped: '{src_path}' — expected a {ALLOWED_EXT} file")
            failed += 1
            continue

        # Existence check
        if not os.path.exists(src_path):
            print(f"⚠  Skipped (not found): {src_path}")
            failed += 1
            continue

        # Read source
        try:
            with open(src_path, "r") as f:
                src = f.read()
        except OSError as e:
            print(f"⚠  Cannot read '{src_path}': {e}")
            failed += 1
            continue

        # Compile
        r = compile_source(src)

        if not r["ok"]:
            print(f"❌ {src_path}")
            for e in r["errors"]:
                print("     ", e)
            print()
            failed += 1
            continue

        # Write artifacts into its own sub-folder
        rank, run_dir, paths = _write_outputs(src_path, r)
        print(f"✅ [{rank}] {src_path}  →  {run_dir}/")
        print(f"     tokens : {len(r['tokens'])}")
        print(f"     ir ops : {len(r['ir'])}")
        for k, p in paths.items():
            print(f"     {k:<6} → {p}")
        print()
        success += 1

    # Summary
    print("─" * 52)
    print(f"Done. {success} succeeded, {failed} failed/skipped.")
    print(f"📒 Log: {LOG_FILE}")

    # Non-zero exit if anything failed (useful for CI / VS Code tasks)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()