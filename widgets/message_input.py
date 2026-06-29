from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QTextOption, QImage
from pathlib import Path

class MessageInput(QTextEdit):
    """
    Поле ввода сообщения.

    Enter        - отправка сообщения
    Shift+Enter  - новая строка
    """

    sendRequested = Signal()
    textChanged2 = Signal(bool)  # True если есть текст, False если пусто
    imagePasted = Signal(QImage)
    fileDropped = Signal(str)  # ← новый сигнал для файлов

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setPlaceholderText("Напишите сообщение...")
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setMinimumHeight(48)
        self.setMaximumHeight(180)
        
        # ✅ Включаем DnD для поля ввода
        self.setAcceptDrops(True)

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
    
    # -----------------------------------------------------
    
    def insertFromMimeData(self, source):
        """Обработка вставки из буфера обмена"""
        # Проверяем, есть ли файлы
        if source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    path = url.toLocalFile()
                    # Если изображение — вставляем как картинку
                    if self._is_image(path):
                        image = QImage(path)
                        if not image.isNull():
                            self.imagePasted.emit(image)
                            return
                    # Иначе — эмитим сигнал с путём к файлу
                    else:
                        self.fileDropped.emit(path)
                        return
            return
        
        # Если есть изображение в буфере
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.imagePasted.emit(image)
                return
        
        # Всё остальное — вставляем как текст
        super().insertFromMimeData(source)
    
    # -----------------------------------------------------
    
    def dropEvent(self, event):
        """Обработка DnD"""
        mime_data = event.mimeData()
        
        if mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                if url.isLocalFile():
                    path = url.toLocalFile()
                    # Эмитим сигнал с путём к файлу
                    self.fileDropped.emit(path)
                    event.acceptProposedAction()
                    return
        
        # Если не файлы — стандартная обработка
        super().dropEvent(event)
    
    # -----------------------------------------------------
    
    def dragEnterEvent(self, event):
        """Разрешаем DnD только для файлов"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    # -----------------------------------------------------
    
    def dragMoveEvent(self, event):
        """Разрешаем перемещение только для файлов"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
    
    # -----------------------------------------------------
    
    def _is_image(self, path: str) -> bool:
        """Проверяет, является ли файл изображением"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff'}
        return Path(path).suffix.lower() in image_extensions