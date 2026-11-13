## THIS IS MADE BY TERRIFIED discord.gg/nixstudios - https://github.com/endclosure

import sys
from PySide6.QtWidgets import QApplication
from ui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("ESP PREVIEWER")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
