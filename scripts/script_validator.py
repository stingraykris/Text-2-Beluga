import sys
import os
import re
import argparse
from PyQt5.QtWidgets import QApplication, QFileDialog
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    
SOUNDS_DIR = BASE_DIR / "assets" / "sounds" / "mp3"

def get_filename():
    """Opens a file dialog and returns the selected filename."""
    app = QApplication(sys.argv)
    options = QFileDialog.Options()
    filename, _ = QFileDialog.getOpenFileName(
        None, "Select Script Text File", "", "Text Files (*.txt);;All Files (*)", options=options
    )
    app.exit()
    return filename

def validate_script_lines(lines):
    """
    Validate the script lines.
    
    Expected structure:
      - An empty line: resets the block state.
      - Lines starting with '#' are comments and are skipped.
      - Lines starting with "WELCOME " are treated as joined messages.
      - The first non-empty, non-comment, non-WELCOME line in a block should be a name line (must contain a colon).
      - Subsequent lines in that block (chat messages) must contain the delimiter '$^' with a valid float duration,
        optionally followed by a sound marker starting with "#!".
      - If a sound marker is present, the referenced sound file (../assets/sounds/mp3/<sound>.mp3) must exist.
    """
    errors = []
    state = "waiting_for_name"  # or "collecting_messages"
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if line == "":
            state = "waiting_for_name"
            continue
        if line.startswith("#"):
            continue
        if line.startswith("WELCOME "):
            continue

        if state == "waiting_for_name":
            # Expect a name line like "Name: rest-of-line"
            if ":" not in line:
                errors.append(f"Line {idx}: Expected a name line containing ':' but got: {line}")
            else:
                name_part = line.split(":", 1)[0].strip()
                if not name_part:
                    errors.append(f"Line {idx}: Name part before ':' is empty.")
            state = "collecting_messages"
        else:
            # In message lines we expect the '$^' delimiter.
            if "$^" not in line:
                errors.append(f"Line {idx}: Expected '$^' delimiter in message line but got: {line}")
            else:
                parts = line.split("$^", 1)
                # The second part should start with a valid duration.
                duration_part = parts[1].strip()
                if duration_part == "":
                    errors.append(f"Line {idx}: Missing duration information after '$^'.")
                else:
                    # Check if a sound marker is included.
                    if "#!" in duration_part:
                        dur_str, sound_marker = duration_part.split("#!", 1)
                        dur_str = dur_str.strip()
                        sound_name = sound_marker.strip()
                        # Check that the sound effect file exists.
                        sound_path = os.path.join(SOUNDS_DIR, f"{sound_name}.mp3")
                        if not os.path.isfile(sound_path):
                            errors.append(f"Line {idx}: Sound effect '{sound_name}' does not exist at expected location: {sound_path}")
                    else:
                        dur_str = duration_part
                    try:
                        float(dur_str)
                    except ValueError:
                        errors.append(f"Line {idx}: Unable to convert duration '{dur_str}' to a number.")
    return errors

def main():
    parser = argparse.ArgumentParser(description="Validate a script text file for chat generation.")
    parser.add_argument("script_file", nargs="?", help="Path to the script text file. If not provided, a file dialog will open.")
    args = parser.parse_args()

    if args.script_file:
        filename = args.script_file
    else:
        filename = get_filename()

    if not filename or not os.path.isfile(filename):
        print("No valid file selected. Exiting.")
        sys.exit(1)

    with open(filename, encoding="utf8") as f:
        lines = f.read().splitlines()

    errors = validate_script_lines(lines)

    if errors:
        print("Script validation found issues:")
        for error in errors:
            print("  -", error)
    else:
        print("Script validation successful: no problems found.")

if __name__ == '__main__':
    # main()
    print('Please run the main.py script!')