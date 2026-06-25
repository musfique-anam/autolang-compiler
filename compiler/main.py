# compiler/main.py
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
def compile_source(src: str, hardware_mode: bool = False) -> dict:
    """Run the full AutoLang pipeline on a source string."""
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

        # Choose the target generator
        if hardware_mode:
            try:
                from .generator_arduino import generate_arduino
                result["cpp"] = generate_arduino(ir)
            except ImportError:
                raise AutoLangError("generator_arduino.py not found. Please create it to use --hardware flag.")
        else:
            result["cpp"] = generate(ir)

    except AutoLangError as e:
        result["ok"] = False
        result["errors"].append(str(e))
    except Exception as e:
        result["ok"] = False
        result["errors"].append(f"Internal error: {e}")

    return result


# =============================================================
#  Output helpers
# =============================================================
def _next_rank() -> str:
    os.makedirs(BUILD_DIR, exist_ok=True)
    existing = [
        name for name in os.listdir(BUILD_DIR)
        if len(name) >= 3 and name[:3].isdigit()
        and os.path.isdir(os.path.join(BUILD_DIR, name))
    ]
    ranks = [int(name[:3]) for name in existing] if existing else [0]
    return f"{max(ranks) + 1:03d}"


def _write_outputs(src_path: str, r: dict, hardware_mode: bool):
    os.makedirs(BUILD_DIR, exist_ok=True)

    rank      = _next_rank()
    stamp     = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = os.path.splitext(os.path.basename(src_path))[0]

    # Arduino CLI requires the .ino file to have the exact same name as its folder.
    sketch_name = f"{rank}_{base_name}"
    
    # Per-run sub-folder
    run_dir = os.path.join(BUILD_DIR, sketch_name)
    os.makedirs(run_dir, exist_ok=True)

    out_ext = ".ino" if hardware_mode else ".cpp"
    
    paths = {
        "code":   os.path.join(run_dir, f"{sketch_name}{out_ext}"),
        "tokens": os.path.join(run_dir, f"{sketch_name}.tokens.txt"),
        "ast":    os.path.join(run_dir, f"{sketch_name}.ast.json"),
        "ir":     os.path.join(run_dir, f"{sketch_name}.ir.txt"),
        "meta":   os.path.join(run_dir, "meta.txt"),
    }

    # 1) Generated C++ / INO
    with open(paths["code"], "w") as f:
        f.write(r["cpp"])

    # 2) Token stream 
    with open(paths["tokens"], "w") as f:
        for t in r["tokens"]:
            f.write(f"{t['type']:<8} {str(t['value']):<15} line={t['line']}\n")

    # 3) AST 
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
        f.write(f"Target    : {'Arduino Hardware' if hardware_mode else 'Simulation'}\n")
        f.write(f"Timestamp : {stamp}\n")

    # 6) Global build log 
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
    print(f"  python -m compiler.main [--hardware] <file{ALLOWED_EXT}> [file2{ALLOWED_EXT} ...]")
    print()
    print("Options:")
    print("  --hardware     Generate Arduino .ino and upload via arduino-cli")
    print("  -h, --help     Show this help message")


def main():
    if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv:
        _print_usage()
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    # Check for the hardware flag
    hardware_mode = "--hardware" in sys.argv
    src_files = [arg for arg in sys.argv[1:] if arg != "--hardware"]

    if not src_files:
        print("⚠  No source files provided.")
        sys.exit(1)

    mode_text = "HARDWARE (Arduino)" if hardware_mode else "SIMULATION (C++)"
    print(f"🛠  AutoLang — Mode: {mode_text}")
    print(f"   Compiling {len(src_files)} file(s) → ./{BUILD_DIR}/\n")

    success = 0
    failed  = 0

    for src_path in src_files:
        if not src_path.endswith(ALLOWED_EXT):
            print(f"⚠  Skipped: '{src_path}' — expected a {ALLOWED_EXT} file")
            failed += 1
            continue

        if not os.path.exists(src_path):
            print(f"⚠  Skipped (not found): {src_path}")
            failed += 1
            continue

        try:
            with open(src_path, "r") as f:
                src = f.read()
        except OSError as e:
            print(f"⚠  Cannot read '{src_path}': {e}")
            failed += 1
            continue

        # Pass the hardware flag to the compiler routine
        r = compile_source(src, hardware_mode)

        if not r["ok"]:
            print(f"❌ {src_path}")
            for e in r["errors"]:
                print("     ", e)
            print()
            failed += 1
            continue

        # Write artifacts 
        rank, run_dir, paths = _write_outputs(src_path, r, hardware_mode)
        print(f"✅ [{rank}] {src_path}  →  {run_dir}/")
        for k, p in paths.items():
            print(f"     {k:<6} → {p}")
        print()
        
        # If we are in hardware mode, trigger the uploader
        if hardware_mode:
            try:
                # Add root to sys path so 'hardware' module can be found
                sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
                from hardware.uploader import upload_to_arduino
                
                print("🚀 Initiating Hardware Upload Sequence...")
                upload_success = upload_to_arduino(paths["code"])
                if not upload_success:
                    failed += 1
            except ImportError:
                print("⚠  Hardware uploader module (hardware/uploader.py) not found. Skipping physical upload.")
                
        success += 1

    print("─" * 52)
    print(f"Done. {success} succeeded, {failed} failed/skipped.")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()