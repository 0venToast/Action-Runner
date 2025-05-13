import sys
import os
import time
import shutil
import subprocess

def safe_delete(file_path):
    """ Attempts to delete the file with retries """
    for _ in range(10):
        try:
            os.remove(file_path)
            print(f"Successfully deleted: {file_path}")
            return True
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            time.sleep(1)  # Retry after 1 second
    return False

def main():
    if len(sys.argv) != 3:
        print("Usage: launcher.exe old_exe_path new_exe_path")
        sys.exit(1)

    old_exe = sys.argv[1]
    new_exe = sys.argv[2]

    print(f"Waiting for main program to exit...")

    # Retry loop to delete the old executable
    for _ in range(20):
        try:
            if safe_delete(old_exe):
                print(f"Old EXE deleted successfully: {old_exe}")
                break
        except Exception as e:
            print(f"Attempt failed with error: {e}")
            time.sleep(1)
    else:
        print("Failed to delete old exe after multiple attempts.")
        sys.exit(1)

    # Try moving the new EXE to replace the old one
    try:
        shutil.move(new_exe, old_exe)
        print(f"Moved new EXE to replace old EXE: {old_exe}")
    except Exception as e:
        print(f"Update failed: {e}")
        sys.exit(1)

    print("Launching updated program...")
    
    # Launch the new program (which has replaced the old one)
    try:
        subprocess.Popen([old_exe])
        print("New program launched.")
    except Exception as e:
        print(f"Failed to launch updated program: {e}")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()