from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ImageViewer(QWidget):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget {
                background: rgba(0,0,0,180);
            }

            QLabel {
                background: transparent;
            }

            QPushButton {
                background: rgba(0,0,0,80);
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 18px;
            }

            QPushButton:hover {
                background: rgba(255,255,255,60);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(36, 36)
        self.close_btn.clicked.connect(self.hide)

        layout.addWidget(self.close_btn, alignment=Qt.AlignRight)

        self.image = QLabel()
        self.image.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.image, 1)

        self._pix = None

    def showImage(self, path):
        self._pix = QPixmap(path)
        self._updatePixmap()
        self.show()
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._updatePixmap()

    def _updatePixmap(self):
        if self._pix is None:
            return

        self.image.setPixmap(
            self._pix.scaled(
                self.width() - 80,
                self.height() - 80,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def mousePressEvent(self, e):
        if self.image.geometry().contains(e.pos()):
            return

        self.hide()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.hide()