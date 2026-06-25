# hardware/uploader.py
import subprocess
import os
import sys

# Dynamically find the local arduino-cli binary in your 'bin' folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOCAL_CLI = os.path.join(PROJECT_ROOT, 'bin', 'arduino-cli')

def get_cli():
    # Use local bin/arduino-cli if it exists, otherwise fall back to system PATH
    if os.path.exists(LOCAL_CLI):
        return LOCAL_CLI
    return "arduino-cli"

def upload_to_arduino(ino_file_path, fqbn="arduino:avr:uno"):
    cli = get_cli()
    print("Detecting connected boards...")
    
    # 1. Detect connected board port
    try:
        detect_result = subprocess.run(
            [cli, "board", "list"], 
            capture_output=True, text=True
        )
    except FileNotFoundError:
        print(f"❌ Error: Could not find arduino-cli executable at {cli}.")
        return False
    
    # Relaxed parsing: Look for standard Linux USB serial ports (ACM or USB)
    lines = detect_result.stdout.split('\n')
    port = None
    for line in lines:
        if "/dev/ttyUSB" in line or "/dev/ttyACM" in line:
            port = line.split()[0]
            break
            
    if not port:
        print("❌ Error: No compatible Arduino board detected on a USB port.")
        print("Current 'arduino-cli board list' output:")
        print(detect_result.stdout)
        return False
        
    print(f"✅ Board found on port: {port}")
    print("Compiling Arduino code...")
    
    # 2. Compile the .ino file
    compile_cmd = [cli, "compile", "--fqbn", fqbn, ino_file_path]
    compile_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if compile_res.returncode != 0:
        print("❌ Compilation Failed:")
        print(compile_res.stderr)
        return False
        
    print("✅ Compilation: SUCCESS")
    print("Uploading to hardware...")
    
    # 3. Upload to the board
    upload_cmd = [cli, "upload", "-p", port, "--fqbn", fqbn, ino_file_path]
    upload_res = subprocess.run(upload_cmd, capture_output=True, text=True)
    
    if upload_res.returncode != 0:
        print("❌ Upload Failed:")
        print(upload_res.stderr)
        return False
        
    print("✅ Upload: SUCCESS")
    print("✅ Execution: RUNNING on physical hardware")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        upload_to_arduino(sys.argv[1])