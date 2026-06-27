import os
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from databend import databend
from files import browse_file, save_file

cleanup_paths = []


# main window
class MainWindow(QMainWindow):
    def __init__(self):
        # main class
        super().__init__()
        self.current_file_path = None

        self.setWindowTitle("My App")
        layout = QVBoxLayout()

        # button that opens file selection dialog
        self.file_button = QPushButton("Get Files:")
        self.file_button.clicked.connect(self.LoadNewImage)
        layout.addWidget(self.file_button)

        self.encoding_box = QComboBox()
        self.encoding_box.addItems(["alaw", "ulaw", "adpcm"])
        self.encoding_box.currentTextChanged.connect(self.Render)
        self.encoding_box_label = QLabel("Select Encoding:")
        encoding_layout = QHBoxLayout()

        encoding_layout.addWidget(self.encoding_box_label)
        encoding_layout.addWidget(self.encoding_box, stretch=1)
        layout.addLayout(encoding_layout)

        self.xor_box = QComboBox()
        self.xor_box.addItems(["Off", "On"])
        self.xor_box.currentTextChanged.connect(self.Render)
        self.xor_box_label = QLabel("Xor Mixing:")
        xor_layout = QHBoxLayout()

        xor_layout.addWidget(self.xor_box_label)
        xor_layout.addWidget(self.xor_box, stretch=1)
        layout.addLayout(xor_layout)

        self.echo_time = QLineEdit()
        self.echo_time.setPlaceholderText("Enter a Number (Decimals Accepted)")
        self.echo_time.setInputMask("00.00;_")
        self.echo_time.editingFinished.connect(self.Render)
        self.echo_time_label = QLabel("Echo Time (Leave blank for no echo):")
        echo_layout = QHBoxLayout()

        echo_layout.addWidget(self.echo_time_label)
        echo_layout.addWidget(self.echo_time, stretch=1)

        layout.addLayout(echo_layout)

        # image from file selection
        builtin_dir = Path(__file__).parent.absolute()
        placeholder_path = builtin_dir / "placeholder.jpg"
        self.image_preview = QLabel()
        self.original_pixmap = QPixmap(str(placeholder_path))
        layout.addWidget(self.image_preview)

        save_button = QPushButton("export image")
        save_button.clicked.connect(self.export_handler)
        layout.addWidget(save_button)

        # container to hold all widgets
        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    # handles window resizes and keeps aspect ratio
    def resizeEvent(self, event):
        super().resizeEvent(event)
        scaled_pixmap = self.original_pixmap.scaled(
            self.image_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_preview.setPixmap(scaled_pixmap)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # loads image from file dialog into pixmap of QLabel
    def LoadNewImage(self):
        path = browse_file()
        if path:
            self.current_file_path = path

            global cleanup_paths
            if path not in cleanup_paths:
                cleanup_paths.append(path)

        self.Render()

    def Render(self):
        if self.current_file_path:
            if self.xor_box.currentText() == "On":
                xor_flag = True
            else:
                xor_flag = False
            try:
                delay_time = float(self.echo_time.text())
            except ValueError:
                delay_time = 0
            synced_files = databend(
                self.current_file_path,
                "/tmp/mash.bmp",
                encoding=self.encoding_box.currentText(),
                use_xor=xor_flag,
                delay_time=delay_time,
            )
            global cleanup_paths
            if synced_files:
                cleanup_paths.extend(synced_files)
            self.original_pixmap = QPixmap("/tmp/mash.bmp")
            scaled_pixmap = self.original_pixmap.scaled(
                self.image_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_preview.setPixmap(scaled_pixmap)

    def export_handler(self):
        (save_file_path) = save_file()
        if save_file_path:
            png_image = Image.open("/tmp/mash.bmp")
            png_image.save(save_file_path)


def cleanup():
    if os.path.exists("/tmp/mash.bmp"):
        os.remove("/tmp/mash.bmp")

    for item in cleanup_paths:
        if isinstance(item, (list, tuple)):
            for sub_item in item:
                if isinstance(sub_item, str) and os.path.exists(sub_item):
                    os.remove(sub_item)

        elif isinstance(item, str) and os.path.exists(item):
            os.remove(item)


# open and show window
app = QApplication()

app.aboutToQuit.connect(cleanup)

window = MainWindow()
window.show()

app.exec()
