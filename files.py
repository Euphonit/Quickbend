import os

from PIL import Image
from PySide6.QtWidgets import QFileDialog


def browse_file():
    input_file_path, _ = QFileDialog.getOpenFileNames(
        None, caption="Select bmp files", filter="Images (*.png *.jpg *.jpeg *.bmp)"
    )

    file_path = []
    if input_file_path:
        for paths in input_file_path:
            imgbeforergb = Image.open(paths)
            img = imgbeforergb.convert("RGB")
            file_basename = os.path.basename(paths)
            name, extension = os.path.splitext(file_basename)
            bmp_filename = name + ".bmp"

            output_path = os.path.join("/tmp", bmp_filename)

            img.save(output_path)
            file_path.append(output_path)
        return file_path


def save_file():
    save_path, _ = QFileDialog.getSaveFileName(
        parent=None, caption="Save file:", filter="Bitmap Files (*.bmp)"
    )
    if save_path:
        return save_path
