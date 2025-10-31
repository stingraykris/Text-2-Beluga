import sys
import os
import json
import re
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPlainTextEdit,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QDoubleSpinBox,
    QScrollArea, QGridLayout, QApplication
)
from PyQt5.QtCore import Qt

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


class EmojiPicker(QWidget):
    """Popup emoji selector."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowTitle("Select Emoji")
        self.setStyleSheet("background-color:#222; color:white; font-size:20px;")
        self.resize(460, 380)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        widget = QWidget()
        grid = QGridLayout(widget)

        emojis = [
            "😀","😁","😂","🤣","😃","😄","😅","😉","😊","😋","😎","😍","😘","😗","😙","😚","🙂","🤗",
            "🤩","🤔","🤨","😐","😑","🙄","😏","😣","😥","😮","🤐","😯","😪","😫","🥱","😴","😌","🤤",
            "😛","😜","😝","🤪","🤓","😒","😞","😔","😕","🙁","☹️","😖","😫","😩","🥺","😢","😭",
            "😠","😡","🤬","😳","🥵","🥶","😱","😨","😰","😥","😓","🤭","🤫","🤥","🤑","🤠",
            "😈","👿","👻","👽","🤖","💀","☠️","🐶","🐱","🐭","🐰","🦊","🐻","🐼","🐨","🐯","🦁","🐮",
            "🌸","🌹","🌻","🌷","🌱","🍀","🍁","🍂","🍃","🍇","🍉","🍊","🍋","🍌","🍍","🥭",
            "🍎","🍒","🍓","🥝","🍞","🥐","🍔","🍕","🍟","🍿","🎂","🍫","🍩","🍪","☕","🍺",
            "🍻","🥂","🍷","🥃","🍸","🎮","🎧","🎤","🎸","🥁","🚗","🚕","🚌","🚀","✈️","💡",
            "💻","📱","📷","🎥","📺","📚","💰","💳","⚙️","🔧","🧰","📅","✏️","📌","🔍",
            "❤️","💙","💚","💛","🧡","💜","🖤","🤍","🤎","💔","✨","🔥","⭐","🌟","☀️"
        ]

        row = col = 0
        for e in emojis:
            btn = QPushButton(e)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet("background:none; border:none; font-size:20px;")
            btn.clicked.connect(lambda _, emoji=e: self.select_emoji(emoji))
            grid.addWidget(btn, row, col)
            col += 1
            if col >= 10:
                col = 0
                row += 1

        scroll.setWidget(widget)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

    def select_emoji(self, emoji):
        self.callback(emoji)
        self.close()


class VisualScriptEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Visual Script Editor")
        self.resize(820, 520)
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: white; font-family: Consolas; }
            QPushButton {
                background-color: #007acc;
                color: white;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #0099ff; }
            QLineEdit, QComboBox, QDoubleSpinBox {
                background: #2b2b2b;
                color: #ffcc6e;
                border: 1px solid #555;
                padding: 4px;
            }
            QListWidget {
                background: #2b2b2b;
                color: #00ffff;
                border: 1px solid #555;
            }
        """)

        self.layout = QVBoxLayout(self)

        # --- Character and Type ---
        char_layout = QHBoxLayout()
        char_layout.addWidget(QLabel("Character:"))
        self.char_combo = QComboBox()
        self.load_characters()
        char_layout.addWidget(self.char_combo)

        char_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Normal", "Joined", "Left", "System", "EmojiOnly"])
        char_layout.addWidget(self.type_combo)
        self.layout.addLayout(char_layout)

        # --- Message input ---
        msg_layout = QHBoxLayout()
        msg_layout.addWidget(QLabel("Message:"))
        self.msg_edit = QPlainTextEdit()
        self.msg_edit.setPlaceholderText("Type your message here… (Shift+Enter for new line)")
        self.msg_edit.setFixedHeight(100)
        self.msg_edit.setStyleSheet("""
            QPlainTextEdit {
                background: #2b2b2b;
                color: #ffcc6e;
                font-family: Consolas, monospace;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 6px;
            }
        """)
        msg_layout.addWidget(self.msg_edit)
        self.layout.addLayout(msg_layout)

        # --- Time, sound, emoji ---
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("Time (sec):"))
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0.01, 600.0)
        self.time_spin.setDecimals(2)
        self.time_spin.setSingleStep(0.1)
        self.time_spin.setValue(2.0)
        opt_layout.addWidget(self.time_spin)

        opt_layout.addWidget(QLabel("Sound:"))
        self.sound_combo = QComboBox()
        self.load_sounds()
        opt_layout.addWidget(self.sound_combo)

        self.emoji_btn = QPushButton("😀 Emoji")
        self.emoji_btn.clicked.connect(self.open_emoji_picker)
        opt_layout.addWidget(self.emoji_btn)
        self.layout.addLayout(opt_layout)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("📂 Load Script")
        self.add_btn = QPushButton("➕ Add")
        self.update_btn = QPushButton("✏️ Update")
        self.delete_btn = QPushButton("🗑 Delete")
        self.save_btn = QPushButton("💾 Save")

        for b in [self.load_btn, self.add_btn, self.update_btn, self.delete_btn, self.save_btn]:
            btn_row.addWidget(b)
        self.layout.addLayout(btn_row)

        # --- Message list ---
        self.msg_list = QListWidget()
        self.layout.addWidget(self.msg_list)
        self.msg_list.itemClicked.connect(self.load_selected_message)
        self.msg_list.currentRowChanged.connect(self.load_selected_row)
        self.msg_list.setFocusPolicy(Qt.StrongFocus)

        # --- Connections ---
        self.load_btn.clicked.connect(self.load_script)
        self.add_btn.clicked.connect(self.add_message)
        self.update_btn.clicked.connect(self.update_message)
        self.delete_btn.clicked.connect(self.delete_message)
        self.save_btn.clicked.connect(self.save_script)

        # --- Data store ---
        self.messages = []

    # ------------------------------------------------------
    def open_emoji_picker(self):
        self.picker = EmojiPicker(self.insert_emoji)
        self.picker.show()

    def insert_emoji(self, emoji):
        self.msg_edit.insert(emoji)

    def load_characters(self):
        self.char_combo.clear()
        path = BASE_DIR / "assets" / "profile_pictures" / "characters.json"
        if path.exists():
            try:
                with open(path, encoding="utf8") as f:
                    data = json.load(f)
                    for name in data.keys():
                        self.char_combo.addItem(name)
            except Exception as e:
                print("Error loading characters.json:", e)

    def load_sounds(self):
        self.sound_combo.clear()
        sounds_dir = BASE_DIR / "assets" / "sounds" / "mp3"
        if sounds_dir.exists():
            for f in sorted(os.listdir(sounds_dir)):
                if f.endswith(".mp3"):
                    self.sound_combo.addItem(f.replace(".mp3", ""))
        self.sound_combo.insertItem(0, "(none)")
        self.sound_combo.setCurrentIndex(0)

    # ------------------------------------------------------
    def add_message(self):
        char = self.char_combo.currentText().strip()
        msg = self.msg_edit.toPlainText().strip()
        sec = float(self.time_spin.value())
        sound = self.sound_combo.currentText().strip()
        mtype = self.type_combo.currentText()

        if not char:
            QMessageBox.warning(self, "Error", "Select a character.")
            return
        if mtype not in ["Joined", "Left", "System", "EmojiOnly"] and not msg:
            QMessageBox.warning(self, "Error", "Enter a message.")
            return

        entry = {
            "char": char,
            "msg": msg,
            "time": sec,
            "sound": sound if sound != "(none)" else "",
            "type": mtype,
        }
        self.messages.append(entry)
        self.refresh_list()
        self.msg_edit.clear()

    def update_message(self):
        idx = self.msg_list.currentRow()
        if idx < 0 or idx >= len(self.messages):
            return

        char = self.char_combo.currentText().strip()
        msg = self.msg_edit.text().strip()
        sec = float(self.time_spin.value())
        sound = self.sound_combo.currentText().strip()
        mtype = self.type_combo.currentText()

        if mtype in ["Joined", "Left"]:
            msg = ""

        new_entry = {
            "char": char,
            "msg": msg,
            "time": sec,
            "sound": sound if sound != "(none)" else "",
            "type": mtype,
        }

        self.messages[idx] = new_entry
        self.refresh_list(select_row=idx)
        self._select_message_by_index(idx)

    def delete_message(self):
        idx = self.msg_list.currentRow()
        if 0 <= idx < len(self.messages):
            del self.messages[idx]
            self.refresh_list()

    def refresh_list(self, select_row=None):
        self.msg_list.blockSignals(True)
        self.msg_list.clear()
        for m in self.messages:
            char = m.get("char", "Unknown")
            msg = m.get("msg", "")
            t = m.get("type", "Normal")
            sec = m.get("time", 1.0)
            snd = m.get("sound", "")

            if t == "Joined":
                desc = f"🟢 {char} joined the chat ({sec}s)"
            elif t == "Left":
                desc = f"🔴 {char} left the chat ({sec}s)"
            elif t == "System":
                desc = f"⚙️ [SYSTEM] {msg} ({sec}s)"
            elif t == "EmojiOnly":
                desc = f"[{char}] {msg} ({sec}s, emoji)"
            else:
                desc = f"[{char}] {msg} ({sec}s, {t})"
            if snd:
                desc += f" 🎵{snd}"
            self.msg_list.addItem(desc)
        self.msg_list.blockSignals(False)
        if self.messages:
            if select_row is not None and 0 <= select_row < len(self.messages):
                self.msg_list.setCurrentRow(select_row)
            elif self.msg_list.currentRow() < 0:
                self.msg_list.setCurrentRow(0)

    # ------------------------------------------------------
    def load_selected_message(self, item):
        idx = self.msg_list.row(item)
        self._select_message_by_index(idx)

    def load_selected_row(self, index):
        self._select_message_by_index(index)

    def _select_message_by_index(self, index):
        """Force full GUI sync, even when switching between Joined/Left and Normal messages."""
        if index < 0 or index >= len(self.messages):
            return

        m = self.messages[index]
        print("message loaded:", m)
        char = m.get("char", "")
        msg = m.get("msg", "")
        mtype = m.get("type", "Normal")
        snd = m.get("sound", "")
        sec = float(m.get("time", 1.0))

        # --- First: ensure message type updates (joined/left disables message box) ---
        self.type_combo.setCurrentText(mtype)
        self.msg_edit.setDisabled(mtype in ["Joined", "Left"])

        # --- Force character refresh even if it's same text as before ---
        if char:
            # Remove selection to force repaint
            self.char_combo.setCurrentIndex(-1)
            QApplication.processEvents()
            self.char_combo.setCurrentText(char)

        # --- Update message text (clear for joined/left) ---
        if mtype in ["Joined", "Left"]:
            self.msg_edit.clear()
        else:
            self.msg_edit.setPlainText(msg)


        # --- Update time ---
        try:
            self.time_spin.setValue(sec)
        except Exception:
            self.time_spin.setValue(1.0)

        # --- Update sound ---
        if snd:
            self.sound_combo.setCurrentText(snd)
        else:
            self.sound_combo.setCurrentText("(none)")

        QApplication.processEvents()

    # ------------------------------------------------------
    def save_script(self):
        """
        Save current self.messages to a .txt file in the exact Beluga format:
        - WELCOME <Name>$^<time>#!<sound>  (for Joined / Left or initial join)
        - <Name>:
        <line1>
        <line2>$^<time>#!<sound>
        - blank line between blocks
        """
        if not self.messages:
            QMessageBox.warning(self, "Empty", "No messages to save.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Script", "", "Text Files (*.txt)")
        if not path:
            return

        def fmt_time(t):
            # compact formatting: 1.0 -> "1", 1.50 -> "1.5", 2.25 -> "2.25"
            try:
                return ("{0:g}".format(float(t)))
            except Exception:
                return "1"

        lines = []
        seen_welcome = set()

        for m in self.messages:
            c = m.get("char", "").strip()
            t = m.get("time", 1.0)
            s = m.get("sound", "").strip()
            typ = m.get("type", "Normal")
            msg = m.get("msg", "")

            # Joined / Left special entries (no message block)
            if typ == "Joined":
                # If saved example expects a time on join, we use t; otherwise keep 1 as default
                time_str = fmt_time(t)
                sound_tag = f"#!{s}" if s else "#!join"
                lines.append(f"WELCOME {c}$^{time_str}{sound_tag}")
                lines.append("")  # blank line after
                continue
            if typ == "Left":
                time_str = fmt_time(t)
                sound_tag = f"#!{s}" if s else "#!leave"
                # some examples use "WELCOME Name left the chat.$^1#!leave"
                lines.append(f"WELCOME {c} left the chat.$^{time_str}{sound_tag}")
                lines.append("")
                continue

            # System message: write as SYSTEM: <text>$^time#!sound
            if typ == "System":
                time_str = fmt_time(t)
                sound_tag = f"#!{s}" if s else ""
                # SYSTEM line contains the message and duration on same line
                if sound_tag:
                    lines.append(f"SYSTEM: {msg}$^{time_str}{sound_tag}")
                else:
                    lines.append(f"SYSTEM: {msg}$^{time_str}")
                lines.append("")
                continue

            # Normal / EmojiOnly messages: write WELCOME once per character (if not already)
            if c and c not in seen_welcome:
                # write a WELCOME line for that character (default 1s join)
                # If you want join to include a sound, you can change sound tag here.
                lines.append(f"WELCOME {c}$^1#!join")
                lines.append("")
                seen_welcome.add(c)

            # Write the character block header
            lines.append(f"{c}:")

            # For multi-line message content, split into lines
            # Only last line gets $^<time> and optional #!sound
            msg_lines = msg.splitlines() or [""]
            time_str = fmt_time(t)
            sound_tag = f"#!{s}" if s else ""

            for i, ln in enumerate(msg_lines):
                if i < len(msg_lines) - 1:
                    # intermediate line — write as-is
                    lines.append(ln)
                else:
                    # last line — append $^time and optional #!sound
                    if sound_tag:
                        lines.append(f"{ln}$^{time_str}{sound_tag}")
                    else:
                        lines.append(f"{ln}$^{time_str}")
            lines.append("")  # blank line after the block

        # write file
        Path(path).write_text("\n".join(lines), encoding="utf8")
        QMessageBox.information(self, "Saved", f"Script saved:\n{path}")


    # ------------------------------------------------------
    def load_script(self):
        """
        Load .txt chat script (Beluga format) and parse into message dicts.
        Supports:
        - WELCOME <name>$^<time>#!join / leave
        - Multi-line messages ending with $^<time>#!<sound>
        - SYSTEM messages
        - Blank lines between blocks
        """
        path, _ = QFileDialog.getOpenFileName(self, "Open Script", "", "Text Files (*.txt)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf8") as f:
                lines = [ln.rstrip("\n") for ln in f.readlines()]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read script:\n{e}")
            return

        self.messages.clear()
        current_char = None
        msg_buffer = []

        def flush_message_block():
            """Convert accumulated lines into one message dict"""
            nonlocal msg_buffer, current_char
            if not current_char or not msg_buffer:
                msg_buffer = []
                return

            full_msg = "\n".join(msg_buffer).strip()
            msg_buffer = []

            # Extract time and sound
            time_val, sound = 1.0, ""
            msg_clean = full_msg
            if "$^" in full_msg:
                parts = full_msg.split("$^", 1)
                msg_clean = parts[0].strip()
                after = parts[1]

                # duration
                match = re.search(r"(\d+(?:\.\d+)?)", after)
                if match:
                    try:
                        time_val = float(match.group(1))
                    except Exception:
                        time_val = 1.0

                # sound
                if "#!" in after:
                    sound = after.split("#!", 1)[1].strip().split()[0]

            self.messages.append({
                "char": current_char,
                "msg": msg_clean,
                "time": time_val,
                "sound": sound,
                "type": "Normal"
            })
            current_char = None

        # --------------------------------------------------
        # MAIN PARSER
        # --------------------------------------------------
        for line in lines:
            line = line.strip()
            print(line)
            if not line:
                # Blank line ends current message block
                flush_message_block()
                continue

            # --- WELCOME (Joined/Left) ---
            if line.startswith("WELCOME "):
                flush_message_block()
                text = line[len("WELCOME "):].strip()

                # detect if it's a "left" message
                if "left the chat" in text:
                    name = text.split("left", 1)[0].strip()
                    # extract optional time/sound
                    match_time = re.search(r"\$\\^(\d+(?:\.\d+)?)", line)
                    time_val = float(match_time.group(1)) if match_time else 1.0
                    sound = "leave"
                    if "#!" in line:
                        sound = line.split("#!", 1)[1].strip().split()[0]
                    self.messages.append({
                        "char": name,
                        "msg": "",
                        "time": time_val,
                        "sound": sound,
                        "type": "Left"
                    })
                    continue

                # joined
                name = text.split("$^", 1)[0].split()[0]
                match_time = re.search(r"\$\\^(\d+(?:\.\d+)?)", line)
                time_val = float(match_time.group(1)) if match_time else 1.0
                sound = "join"
                if "#!" in line:
                    sound = line.split("#!", 1)[1].strip().split()[0]
                self.messages.append({
                    "char": name,
                    "msg": "",
                    "time": time_val,
                    "sound": sound,
                    "type": "Joined"
                })
                continue

            # --- SYSTEM message ---
            if line.upper().startswith("SYSTEM:"):
                flush_message_block()
                text = line[len("SYSTEM:"):].strip()
                msg_clean = text
                time_val, sound = 1.0, ""
                if "$^" in text:
                    parts = text.split("$^", 1)
                    msg_clean = parts[0].strip()
                    after = parts[1]
                    match = re.search(r"(\d+(?:\.\d+)?)", after)
                    if match:
                        try:
                            time_val = float(match.group(1))
                        except Exception:
                            time_val = 1.0
                    if "#!" in after:
                        sound = after.split("#!", 1)[1].strip().split()[0]
                self.messages.append({
                    "char": "SYSTEM",
                    "msg": msg_clean,
                    "time": time_val,
                    "sound": sound,
                    "type": "System"
                })
                continue

            # --- Character header (e.g. Sana:) ---
            if line.endswith(":"):
                flush_message_block()
                current_char = line[:-1].strip()
                continue

            # --- Message line ---
            if current_char:
                msg_buffer.append(line)

        # Final flush
        flush_message_block()

        # Refresh list widget
        self.populate_message_list()
        QMessageBox.information(self, "Loaded", f"Loaded {len(self.messages)} messages from:\n{path}")
        
    def populate_message_list(self):
        """Refresh the message list widget from self.messages."""
        if not hasattr(self, "msg_list"):
            return  # no list widget exists yet

        self.msg_list.clear()

        for m in self.messages:
            c = m.get("char", "")
            msg = m.get("msg", "")
            typ = m.get("type", "Normal")

            if typ == "Joined":
                text = f"🟢 {c} joined the chat"
            elif typ == "Left":
                text = f"🔴 {c} left the chat"
            elif typ == "System":
                text = f"⚙️ SYSTEM: {msg}"
            else:
                # For normal messages show short preview
                preview = msg.split("\n")[0]
                if len(preview) > 60:
                    preview = preview[:60] + "..."
                text = f"{c}: {preview}"

            self.msg_list.addItem(text)



# For testing standalone
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = VisualScriptEditor()
    w.show()
    sys.exit(app.exec_())
