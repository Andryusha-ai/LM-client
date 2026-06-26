from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QTextEdit


class MessageInput(QTextEdit):
    """
    Поле ввода сообщения.

    Enter        - новая строка
    Ctrl+Enter   - отправка сообщения
    """

    sendRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setPlaceholderText("Напишите сообщение...")

        self.setAcceptRichText(False)

        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        self.setMinimumHeight(48)
        self.setMaximumHeight(180)

        self.document().contentsChanged.connect(self._update_height)

    # -----------------------------------------------------

    def keyPressEvent(self, event):

        if (
            event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and event.modifiers() & Qt.ControlModifier
        ):
            self.sendRequested.emit()
            return

        super().keyPressEvent(event)

    # -----------------------------------------------------

    def _update_height(self):

        doc_height = self.document().size().height()

        new_height = max(
            48,
            min(
                int(doc_height + 16),
                180,
            ),
        )

        self.setFixedHeight(new_height)

    # -----------------------------------------------------

    def message(self):

        return self.toPlainText().strip()

    # -----------------------------------------------------

    def clearMessage(self):

        self.clear()