# widgets/message_card.py
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QSizePolicy,
    QAbstractScrollArea,
)


class MessageCard(QFrame):
    """
    Карточка одного сообщения.

    role:
        "user"
        "assistant"
        "system"
    """

    def __init__(self, role: str, text: str = "", parent=None):
        super().__init__(parent)

        self.role = role

        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        self.title = QLabel(self._title())
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.text = QTextBrowser()
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.text.setOpenExternalLinks(True)
        self.text.setFrameShape(QFrame.NoFrame)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.text.document().setDefaultTextOption(text_option)

        self.text.setMarkdown(text)

        layout.addWidget(self.title)
        layout.addWidget(self.text)

        self._apply_style()

    # --------------------------------------------------

    def _title(self):
        if self.role == "user":
            return "Вы"
        if self.role == "assistant":
            return "Ассистент"
        return "Система"

    # --------------------------------------------------

    def _apply_style(self):
        if self.role == "user":
            title_color = "#555555"
        elif self.role == "assistant":
            title_color = "#555555"
        else:
            title_color = "#aa4444"

        self.setStyleSheet(f"""
            QFrame {{
                border: none;
                background: transparent;
            }}
            QLabel {{
                font-weight: bold;
                font-size: 12px;
                color: {title_color};
            }}
            QTextBrowser {{
                border: none;
                background: transparent;
                color: #111111;
            }}
        """)

    # --------------------------------------------------

    def sizeHint(self):
        doc_height = int(self.text.document().size().height())
        title_height = self.title.sizeHint().height()
        return QSize(self.width(), doc_height + title_height + 28)

    # --------------------------------------------------

    def setText(self, text: str):
        self.text.setMarkdown(text)

        self.text.document().adjustSize()

        self.text.setFixedHeight(
            int(self.text.document().size().height()) + 8
        )

        self.text.adjustSize()

        self.adjustSize()
        self.updateGeometry()

    # --------------------------------------------------

    def appendText(self, text: str):
        print("append")
        cursor = self.text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.text.setTextCursor(cursor)

        # пересчитать высоту QTextBrowser
        self.text.document().adjustSize()
        h = int(self.text.document().size().height()) + 8
        self.text.setFixedHeight(h)

        self.updateGeometry()
        self.adjustSize()
        print(
            self.height(),
            self.text.height(),
            self.text.document().size().height()
        )

    # --------------------------------------------------

    def markdown(self):
        return self.text.toMarkdown()
