from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QTextOption, QImage

class MessageInput(QTextEdit):
    """
    Поле ввода сообщения.

    Enter        - отправка сообщения
    Shift+Enter  - новая строка
    """

    sendRequested = Signal()
    textChanged2 = Signal(bool)  # True если есть текст, False если пусто
    imagePasted = Signal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setPlaceholderText("Напишите сообщение...")
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setMinimumHeight(48)
        self.setMaximumHeight(180)

        self.document().contentsChanged.connect(self._update_height)
        self.document().contentsChanged.connect(self._emit_has_text)
        self._update_height()

    # -----------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                # Shift+Enter — новая строка
                super().keyPressEvent(event)
            else:
                # Enter — отправка
                self.sendRequested.emit()
            return
        super().keyPressEvent(event)

    # -----------------------------------------------------

    def _update_height(self):
        doc_height = self.document().size().height()
        new_height = max(48, min(int(doc_height + 16), 180))
        self.setFixedHeight(new_height)

    def _emit_has_text(self):
        self.textChanged2.emit(bool(self.toPlainText().strip()))

    # -----------------------------------------------------

    def message(self):
        return self.toPlainText().strip()

    def clearMessage(self):
        self.clear()
        self._update_height()
    # ---------------------------------------------------------
    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()

            if isinstance(image, QImage):
                self.imagePasted.emit(image)

            return

        super().insertFromMimeData(source)