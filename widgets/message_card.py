# widgets/message_card.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QSizePolicy,
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

        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.title = QLabel(self._title())
        self.text = QTextBrowser()

        self.text.setOpenExternalLinks(True)
        self.text.setFrameShape(QFrame.NoFrame)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Исправлено: создаем QTextOption с правильным параметром
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
            self.setStyleSheet("""
                QFrame {
                    border:1px solid #3f3f46;
                    border-radius:10px;
                    background:#303030;
                }
                QLabel {
                    font-weight:bold;
                }
                QTextBrowser {
                    border:none;
                    background:transparent;
                }
            """)
        elif self.role == "assistant":
            self.setStyleSheet("""
                QFrame {
                    border:1px solid #404040;
                    border-radius:10px;
                    background:#252525;
                }
                QLabel {
                    font-weight:bold;
                }
                QTextBrowser {
                    border:none;
                    background:transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    border:1px solid #555;
                    border-radius:10px;
                    background:#1f1f1f;
                }
                QLabel {
                    font-weight:bold;
                    color:#d99;
                }
                QTextBrowser {
                    border:none;
                    background:transparent;
                }
            """)

    # --------------------------------------------------

    def setText(self, text: str):
        self.text.setMarkdown(text)

    # --------------------------------------------------

    def appendText(self, text: str):
        cursor = self.text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.text.setTextCursor(cursor)

    # --------------------------------------------------

    def markdown(self):
        return self.text.toMarkdown()