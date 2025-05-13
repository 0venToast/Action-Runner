import sys
import os
import time
import shutil
import subprocess

def main():
    if len(sys.argv) != 3:
        print("Usage: launcher.exe old_exe_path new_exe_path")
        sys.exit(1)

    old_exe = sys.argv[1]
    new_exe = sys.argv[2]

    print("Waiting for main program to exit...")
    for _ in range(20):
        try:
            os.remove(old_exe)
            break
        except:
            time.sleep(1)
    else:
        print("Failed to delete old exe.")
        sys.exit(1)

    try:
        shutil.move(new_exe, old_exe)
    except Exception as e:
        print("Update failed:", e)
        sys.exit(1)

    print("Launching updated program...")
    subprocess.Popen([old_exe])
    sys.exit(0)

if __name__ == "__main__":
    main()