#  main.py – FULL GUI VERSION
# --------------------------------------------------------------
import sys
import os
import shutil
import datetime
from pathlib import Path
from playsound import playsound
import json
#  Your existing functions (imported exactly as you had)
# ----------------------------------------------------------------
from generate_chat import get_filename as get_chat_filename, save_images
from compile_images import gen_vid
from script_validator import get_filename as get_validator_filename, validate_script_lines
from script_editor import VisualScriptEditor

#  PyQt5 imports
# ----------------------------------------------------------------
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QDialog, QPushButton, QFileDialog,
    QProgressDialog, QTextEdit, QHBoxLayout, QFrame,
    QLineEdit, QColorDialog, QFormLayout, QMessageBox

)
from PyQt5.QtGui import QFont, QFontDatabase, QColor, QPalette, QPixmap, QPainter, QPainterPath
from PyQt5.QtCore import Qt, QEvent,QUrl, QObject, QThread, pyqtSignal

from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

#  BASE_DIR – works for .py and .exe
# ----------------------------------------------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

#  Worker thread for long tasks
# ----------------------------------------------------------------
class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()
            
#  Helper – modal message box
# ----------------------------------------------------------------

def show_message(title: str, text: str, color: str = "#80ff56"):
    """
    Shows a modal dialog with scrollable text.
    Perfect for long error lists with multiple lines.
    """
    dlg = QDialog()
    dlg.setWindowTitle(title)
    dlg.setFixedSize(600, 400)  # Wider + taller for readability

    layout = QVBoxLayout()

    # Scrollable text area #ff5555
    text_edit = QTextEdit()
    text_edit.setPlainText(text)
    text_edit.setReadOnly(True)
    text_edit.setStyleSheet("""
        QTextEdit {
            background: #1e1e1e;
            color: """ + color + """;
            font-family: Consolas, monospace;
            font-size: 12px;
            padding: 10px;
            border: 1px solid #444;
        }
    """)
    layout.addWidget(text_edit)

    # OK button
    ok_btn = QPushButton("OK")
    ok_btn.clicked.connect(dlg.accept)
    layout.addWidget(ok_btn)

    dlg.setLayout(layout)
    dlg.exec_()
    
#  Helper – load a custom font (safe)
# ----------------------------------------------------------------
def load_custom_font():
    font_path = BASE_DIR / "assets" / "fonts" / "whitney" / "medium.ttf"
    if not font_path.is_file():
        print(f"[WARN] Font not found: {font_path}")
        return None

    db = QFontDatabase()
    font_id = db.addApplicationFont(str(font_path))
    if font_id == -1:
        print(f"[WARN] Could not load font: {font_path}")
        return None

    families = db.applicationFontFamilies(font_id)
    if families:
        print(f"[INFO] Loaded custom font: {families[0]}")
        return families[0]
    return None

#  LOAD SCRIPT FILE FROM FILE SYSTEM – GUI version
# ----------------------------------------------------------------
def load_script_file(parent=None):
    """
    Opens file picker, reads .txt file.
    Returns (filename: str, lines: list) or (None, None) if cancelled/error.
    """
    if parent is None:
        parent = QApplication.instance().activeWindow()

    filename, _ = QFileDialog.getOpenFileName(
        parent=parent,
        caption="Select Script File",
        directory=str(BASE_DIR),
        filter="Text files (*.txt);;All files (*.*)"
    )
    if not filename:
        return None, None

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        return filename, lines
    except Exception as e:
        show_message("Read Error", f"Failed to read file:\n{e}", color="#ff5555")
        return None, None
    
#  VALIDATE SHOW ON SCREEN – GUI version
# ----------------------------------------------------------------
def validate_and_show(lines, parent=None):
    """
    Runs validation and shows GUI result.
    Returns True if valid, False if errors.
    """
    if parent is None:
        parent = QApplication.instance().activeWindow()

    prog = QProgressDialog("Validating script...", None, 0, 0, parent)
    prog.setWindowTitle("Validating...")
    prog.setWindowModality(Qt.WindowModal)
    prog.setMinimumDuration(0)
    prog.setFixedWidth(500)
    prog.setCancelButton(None)
    prog.show()
    QApplication.processEvents()

    try:
        errors = validate_script_lines(lines)
    except Exception as e:
        prog.close()
        show_message("Validation Error", f"validate_script_lines() failed:\n{e}", color="#ff5555")
        return False
    finally:
        prog.close()

    if errors:
        #show_message("Validation Failed", "Script has issues:\n\n" + "\n".join(errors))
        show_message("Validation Failed", "Script has issues:\n\n" + "\n".join(errors), color="#ff5555")
        return False
    else:
        show_message("Valid!", "Script passed validation! Ready to generate video.")
        return True

#  VALIDATE SCRIPT – GUI version
# ----------------------------------------------------------------
def print_instructions():
    items = [
        "> Your chat script should be written in a [.txt] file with the following formatting guidelines:",
        "--IMPORTANT__POINTS--",
        "- Any custom characters should be configured in [assets/profile_pictures/characters.json] and their profile pictures should be present.",
        "- All the dependencies listed in [requirements.txt] should be installed.",
        "",
        "--FORMATTING__GUIDELINES--",
        "- Lines beginning with a hashtag (#) are treated as comments and are ignored.",
        "- To display a \"character joined\" message, the line should begin with WELCOME followed by the character name ~ [WELCOME CharacterName]",
        "- To make a character say something, Write the character's name immediately followed by a colon and it's messages in the subsequent lines.",
        "- Each message should be (MANDATORILY) immediately followed by \"$^\" and a number that indicated for how many seconds that message should be shown.",
        "- Each duration can be (OPTIONALLY) immediately followed by \"#!\" and a sound effect name to play that sound in the video when that message is shown.",
        "- There should be an empty line between a character's message and the next character's name.",
        "- Message text enclosed within ** and ** will be shown in bold.",
        "- Message text enclosed within __ and __ will be shown in italics.",
        "- Emojis are supported in messages.",
        "- Different characters can be mentioned in a message by writing \"@\" followed by a character's name.",
        "",
        "- An example script has been provided to give an idea and get you started.",
        "",
        "",
    ]
    header = "Formatting"
    if isinstance(items, list):
        # Join items with line breaks (or bullet points)
        content = "\r\n".join(f"• {item}" for item in items)
    else:
        # If it's just plain text
        content = str(items)
    show_message("Formatting", content, color="#ffff56")
    
#  VALIDATE SCRIPT – GUI version
# ----------------------------------------------------------------
def run_validate_script():
    """Standalone validator – uses the two parts."""
    filename, lines = load_script_file()
    if lines is not None:
        validate_and_show(lines)
        
#  GENERATE CHAT – GUI version
# ----------------------------------------------------------------
def run_generate_chat():
    CHAT_DIR = BASE_DIR / "chat"
    FINAL_VIDEO = BASE_DIR / "final_video.mp4"

    if FINAL_VIDEO.is_file():
        FINAL_VIDEO.unlink()
    if CHAT_DIR.exists():
        shutil.rmtree(CHAT_DIR, ignore_errors=True)

    parent = QApplication.instance().activeWindow() if QApplication.instance() else None
    # Step 1: Load file
    filename, lines = load_script_file()
    if lines is None:
        return  # Cancelled or error

    # Step 2: VALIDATE FIRST
    if not validate_and_show(lines):
        return  # Stop if invalid
    now = datetime.datetime.now()

    # ---- STEP 1 – images ------------------------------------------------
    prog = QProgressDialog("Generating chat images …", "Cancel", 0, 0,parent)
    prog.setWindowTitle("Step 1 / 2")
    prog.setModal(True)
    prog.setWindowModality(Qt.WindowModal)
    prog.setFixedWidth(300)
    prog.setCancelButton(None)
    prog.setMinimumDuration(0)
    prog.show()
    
    thread = QThread()
    worker = Worker(save_images, lines, now)
    worker.moveToThread(thread)
    worker.finished.connect(thread.quit)
    worker.finished.connect(prog.close)
    worker.error.connect(lambda e: show_message("Image Error", e, color="#ff5555"))
    thread.started.connect(worker.run)
    thread.start()

    while thread.isRunning():
        QApplication.processEvents()

    # try:
    #     save_images(lines, init_time=now)
    # except Exception as e:
    #     prog.close()
    #     show_message("Image Error", f"save_images() failed:\n{e}", color="#ff5555")
    #     return
    # finally:
    #     prog.close()

    # ---- STEP 2 – video -------------------------------------------------
    prog = QProgressDialog("Compiling video …", "Cancel", 0, 0, parent)
    prog.setWindowTitle("Step 2 / 2")
    prog.setModal(True)
    prog.setWindowModality(Qt.WindowModal)
    prog.setCancelButton(None)
    prog.setFixedWidth(300)
    prog.setMinimumDuration(0)
    prog.show()
    
    thread = QThread()
    worker = Worker(gen_vid, filename)
    worker.moveToThread(thread)
    worker.finished.connect(thread.quit)
    worker.finished.connect(prog.close)
    worker.error.connect(lambda e: show_message("Video Error", e, color="#ff5555"))
    thread.started.connect(worker.run)
    thread.start()

    while thread.isRunning():
        QApplication.processEvents()
        
    # try:
    #     gen_vid(filename)
    # except Exception as e:
    #     prog.close()
    #     show_message("Video Error", f"gen_vid() failed:\n{e}", color="#ff5555")
    #     return
    # finally:
    #     prog.close()

    # ---- SUCCESS --------------------------------------------------------
    show_message(
        "Completed!",
        f"Video → {FINAL_VIDEO}\n"
        f"Images → {CHAT_DIR}\n\n"
        "Press OK to return."
    )
    # open video (Windows)
    if FINAL_VIDEO.is_file():
        try:
            os.startfile(str(FINAL_VIDEO))
        except Exception:
            pass

#  SOUNDS WINDOW – GUI version
# ----------------------------------------------------------------
class SoundsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sound Manager")
        self.resize(500, 350)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.layout = QVBoxLayout(self)

        # --- Header ---
        header = QLabel("🎵 Sound Library")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffcc6e;")
        header.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(header)

        # --- Sound List ---
        self.sound_list = QListWidget()
        self.sound_list.setStyleSheet("""
            QListWidget {
                background: #2b2b2b;
                border: 1px solid #444;
                color: #00ffff;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            QListWidget::item:selected {
                background: #444;
                color: #ffcc6e;
            }
        """)
        self.layout.addWidget(self.sound_list)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play Sound")
        self.add_btn = QPushButton("+ Add Sound")
        self.delete_btn = QPushButton("🗑 Delete Sound")

        for btn in [self.play_btn, self.add_btn, self.delete_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #007acc;
                    color: white;
                    border-radius: 5px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #0099ff;
                }
            """)

        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.delete_btn)
        self.layout.addLayout(button_layout)

        # --- Paths ---
        self.sounds_dir = BASE_DIR / "assets" / "sounds" / "mp3"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)

        # --- Player ---
        self.player = QMediaPlayer()

        # --- Events ---
        self.play_btn.clicked.connect(self.play_selected_sound)
        self.add_btn.clicked.connect(self.add_sound)
        self.delete_btn.clicked.connect(self.delete_sound)
        self.sound_list.itemDoubleClicked.connect(self.play_sound)

        # Load existing sounds
        self.populate_sounds()

    def populate_sounds(self):
        """Populate the sound list with all mp3 files"""
        self.sound_list.clear()
        for file in sorted(os.listdir(self.sounds_dir)):
            if file.endswith(".mp3"):
                self.sound_list.addItem(file.replace(".mp3", ""))

    def play_sound(self, item):
        """Triggered by double-click"""
        self._play_file(item.text())

    def play_selected_sound(self):
        """Triggered by Play button"""
        item = self.sound_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a sound to play.")
            return
        self._play_file(item.text())

    def _play_file(self, name):
        """Shared logic for playing a file"""
        file_path = self.sounds_dir / f"{name}.mp3"
        if not file_path.exists():
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            return

        url = QUrl.fromLocalFile(str(file_path))
        self.player.setMedia(QMediaContent(url))
        self.player.setVolume(80)
        self.player.play()

    def add_sound(self):
        """Add new sound"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Sound File", "", "MP3 Files (*.mp3)"
        )
        if not file_path:
            return

        dest_file = self.sounds_dir / os.path.basename(file_path)
        if dest_file.exists():
            QMessageBox.warning(self, "Exists", f"Sound '{dest_file.name}' already exists.")
            return

        shutil.copy(file_path, dest_file)
        self.populate_sounds()
        QMessageBox.information(self, "Added", f"Added: {dest_file.name}")

    def delete_sound(self):
        """Delete selected sound"""
        item = self.sound_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a sound to delete.")
            return

        sound_file = self.sounds_dir / f"{item.text()}.mp3"
        confirm = QMessageBox.question(
            self, "Confirm Delete", f"Delete sound '{sound_file.name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes and sound_file.exists():
            os.remove(sound_file)
            self.populate_sounds()
            QMessageBox.information(self, "Deleted", f"Deleted: {sound_file.name}")

#  CHARACTER  – GUI version
# ----------------------------------------------------------------
class AddCharacterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Character")
        self.resize(300, 200)
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.color_input = QLineEdit("#ffffff")
        self.image_path = QLineEdit()
        self.browse_btn = QPushButton("Browse Image")
        self.pick_color_btn = QPushButton("Pick Color")
        self.save_btn = QPushButton("Save")

        self.pick_color_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007acc;
                        color: white;
                        border-radius: 5px;
                        margin: 10px;
                        padding: 6px;
                    }
                    QPushButton:hover {
                        background-color: #0099ff;
                    }
                """)

        self.browse_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007acc;
                        color: white;
                        border-radius: 5px;
                        padding: 6px;
                        margin: 10px;
                    }
                    QPushButton:hover {
                        background-color: #0099ff;
                    }
                """)

        self.save_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #019345;
                        color: white;
                        border-radius: 5px;
                        padding: 6px;
                        margin: 10px;
                    }
                    QPushButton:hover {
                        background-color: #00cc5f;
                    }
                """)


        layout.addRow("Name:", self.name_input)
        layout.addRow("Role Color:", self.color_input)
        layout.addRow(self.pick_color_btn)
        layout.addRow("Profile Image:", self.image_path)
        layout.addRow(self.browse_btn)

        
        layout.addRow(self.save_btn)

        self.browse_btn.clicked.connect(self.select_image)
        self.pick_color_btn.clicked.connect(self.pick_color)
        self.save_btn.clicked.connect(self.accept)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.image_path.setText(file_path)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_input.setText(color.name())

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "color": self.color_input.text().strip(),
            "image": self.image_path.text().strip(),
        }


class CharacterViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Character Viewer")
        self.resize(550, 380)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        # Layouts
        main_layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # --- LEFT SIDE ---
        self.char_list = QListWidget()
        self.char_list.setStyleSheet("""
            QListWidget {
                background: #2b2b2b;
                border: 1px solid #444;
                color: #00ffff;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            QListWidget::item:selected {
                background: #444;
                color: #ffcc6e;
            }
        """)
        self.char_list.itemClicked.connect(self.show_character_info)

        self.add_btn = QPushButton("+ Add Character")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border-radius: 5px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #0099ff;
            }
        """)
        self.add_btn.clicked.connect(self.add_character)

        left_layout.addWidget(QLabel("Characters"))
        left_layout.addWidget(self.char_list)
        left_layout.addWidget(self.add_btn)

        # --- RIGHT SIDE ---
        self.profile_pic = QLabel()
        self.profile_pic.setAlignment(Qt.AlignCenter)
        self.profile_pic.setFixedSize(180, 180)
        self.name_label = QLabel("Select a character")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.color_frame = QFrame()
        self.color_frame.setFixedHeight(30)
        self.color_frame.setStyleSheet("background-color: #333; border-radius: 5px;")

        right_layout.addWidget(self.profile_pic)
        right_layout.addWidget(self.name_label)
        right_layout.addWidget(self.color_frame)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        # Data
        self.characters_dict = self.load_characters()
        self.populate_list()

    def load_characters(self):
        json_path = BASE_DIR / "assets" / "profile_pictures" / "characters.json"
        try:
            with open(json_path, encoding="utf8") as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading characters.json: {e}")
            return {}

    def save_characters(self):
        json_path = BASE_DIR / "assets" / "profile_pictures" / "characters.json"
        with open(json_path, "w", encoding="utf8") as file:
            json.dump(self.characters_dict, file, indent=4, ensure_ascii=False)

    def populate_list(self):
        self.char_list.clear()
        for name in self.characters_dict.keys():
            self.char_list.addItem(name)

    def show_character_info(self, item):
        name = item.text()
        info = self.characters_dict.get(name)
        if not info:
            return

        color = info.get("role_color", "#ffffff")
        pic_path = BASE_DIR / "assets" / "profile_pictures" / info.get("profile_pic", "")

        # Update text and color
        self.name_label.setText(name)
        self.color_frame.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.profile_pic.setStyleSheet(f"""
            QLabel {{
                border: 3px solid {color};
                border-radius: 90px;
                background: #2b2b2b;
            }}
        """)

        # Rounded picture
        if pic_path.exists():
            pixmap = QPixmap(str(pic_path)).scaled(180, 180, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            rounded = QPixmap(pixmap.size())
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 180, 180)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            self.profile_pic.setPixmap(rounded)
        else:
            self.profile_pic.setPixmap(QPixmap())

    def add_character(self):
        dialog = AddCharacterDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            name, color, img_path = data["name"], data["color"], data["image"]

            if not name or not os.path.exists(img_path):
                QMessageBox.warning(self, "Error", "Please enter a valid name and select an image.")
                return

            # Copy image
            dest_dir = BASE_DIR / "assets" / "profile_pictures" / "perm"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / os.path.basename(img_path)
            shutil.copy(img_path, dest_file)

            rel_path = f"perm/{dest_file.name}"
            self.characters_dict[name] = {"profile_pic": rel_path, "role_color": color}
            self.save_characters()
            self.populate_list()
            QMessageBox.information(self, "Success", f"Character '{name}' added!")



#  GUI MENU
# ----------------------------------------------------------------
class BelugaMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text 2 Beluga")
        self.setFixedSize(720, 420)

        # ----- background / palette -------------------------------------------------
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor("#171717"))
        pal.setColor(QPalette.WindowText, QColor("#d4e9ff"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        # ----- main layout ---------------------------------------------------------
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ----- header --------------------------------------------------------------
        hdr = QLabel("🎥 Text 2 Beluga")
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet("font-size:28pt; font-weight:bold; color:#ffcc6e;")
        main_layout.addWidget(hdr)

        # ----- description ---------------------------------------------------------
        desc = QLabel(
            "> Welcome to Text2Beluga! Easily generate a Beluga-like video from a simple "
            "text file script within seconds. The best part? It's absolutely free!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size:12pt; color:#d4e9ff;")
        main_layout.addWidget(desc)

        # ----- menu list -----------------------------------------------------------
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background:#212121;
                border:1px solid #444;
                color:#00ffff;
                padding:10px;
                font-family: Consolas, monospace;
            }
            QListWidget::item:selected {
                background:#444;
                color:#ffcc6e;
            }
        """)
        self.list_widget.setFocusPolicy(Qt.StrongFocus)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # try to use the custom font – fallback to Consolas if missing
        custom_family = load_custom_font()
        item_font = QFont(custom_family or "Consolas", 12)
        self.list_widget.setFont(item_font)

        menu_items = ["Generate Video", "Script Editor", "Characters", "Sounds", "Validate Script", "Instructions", "Exit"]
        for txt in menu_items:
            if txt:
                item = QListWidgetItem(txt)
                self.list_widget.addItem(item)

        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.installEventFilter(self)          # j/k, arrows, Enter
        main_layout.addWidget(self.list_widget)

        self.setLayout(main_layout)

        # start on first real entry
        self.list_widget.setCurrentRow(0)

    # ----------------------------------------------------------------
    #  Key handling (j/k, arrows, Enter)
    # ----------------------------------------------------------------
    def eventFilter(self, source, event):
        if source is self.list_widget and event.type() == QEvent.KeyPress:
            key = event.key()
            cur = self.list_widget.currentRow()
            max_row = self.list_widget.count() - 1

            if key in (Qt.Key_Up, Qt.Key_K):
                new = (cur - 1) if cur > 0 else max_row
                self.list_widget.setCurrentRow(new)
                return True
            if key in (Qt.Key_Down, Qt.Key_J):
                new = (cur + 1) if cur < max_row else 0
                self.list_widget.setCurrentRow(new)
                return True
            if key in (Qt.Key_Enter, Qt.Key_Return):
                self.on_item_clicked(self.list_widget.currentItem())
                return True
        return super().eventFilter(source, event)

    # ----------------------------------------------------------------
    #  Action when an item is selected
    # ----------------------------------------------------------------
    def on_item_clicked(self, item):
        if not item or not item.text():
            return

        txt = item.text()
        if txt == "Generate Video":
            run_generate_chat()
        elif txt == "Validate Script":
            run_validate_script()
        elif txt == "Instructions":
            print_instructions()
        elif txt == "Sounds":
            self.sounds_window = SoundsWindow()
            self.sounds_window.show()
        elif txt == "Characters":
            self.viewer = CharacterViewer()
            self.viewer.show()
            CharacterViewer
        elif txt == "Script Editor":
            self.editor_window = VisualScriptEditor()
            self.editor_window.show()
        elif txt == "Exit":
            self.close()
            
# ----------------------------------------------------------------
#  Entry point
# ----------------------------------------------------------------
def show_gui_menu():
    app = QApplication(sys.argv)
    win = BelugaMenu()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    show_gui_menu()