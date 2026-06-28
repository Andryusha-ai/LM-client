# ui.py
import os
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QPainter, QColor, QPen, QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QLabel,
    QFrame,
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton
)
from pathlib import Path
from datetime import datetime
from cache_manager import CacheManager

from widgets.message_card import MessageCard
from widgets.message_input import MessageInput
from widgets.attachment_bar import AttachmentBar
from widgets.image_viewer import ImageViewer

class SettingsDialog(QDialog):
    def __init__(self, current_api_url, current_api_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки подключения")
        self.setMinimumWidth(350)
        
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Поля ввода
        self.api_url_input = QLineEdit(current_api_url)
        self.api_key_input = QLineEdit(current_api_key)
        self.api_key_input.setEchoMode(QLineEdit.Password) # Чтобы ключ звёздочками закрывался

        layout.addRow("API URL:", self.api_url_input)
        layout.addRow("API Ключ:", self.api_key_input)

        # Кнопка сохранения
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.accept) # Закрывает диалог с кодом QDialog.Accepted
        layout.addRow(self.save_button)

    def get_values(self):
        return {
            "api_url": self.api_url_input.text().strip(),
            "api_key": self.api_key_input.text().strip()
        }

class SmartButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "mic"  # "mic" | "send" | "stop"
        self.setFixedSize(44, 44)
        self.setCursor(Qt.PointingHandCursor)

    def setSendMode(self, enabled: bool):
        if self._mode == "stop":
            return
        self._mode = "send" if enabled else "mic"
        self.setToolTip("Отправить" if enabled else "Запись голоса")
        self.update()

    def setStopMode(self, enabled: bool):
        self._mode = "stop" if enabled else "mic"
        self.setToolTip("Остановить" if enabled else "Запись голоса")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2

        if self._mode == "send":
            pen = QPen(QColor("#ffffff"), 2)
            painter.setPen(pen)
            painter.drawLine(cx - 8, cy + 6, cx + 8, cy - 6)
            painter.drawLine(cx + 8, cy - 6, cx + 1, cy - 6)
            painter.drawLine(cx + 8, cy - 6, cx + 8, cy + 1)
        elif self._mode == "stop":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#ffffff"))
            painter.drawRect(cx - 8, cy - 8, 16, 16)
        else:
            pen = QPen(QColor("#555555"), 2)
            painter.setPen(pen)
            heights = [14, 20, 14]
            w = 4
            gap = 5
            start_x = cx - (len(heights) * (w + gap) - gap) // 2
            for i, h in enumerate(heights):
                x = start_x + i * (w + gap)
                y = cy - h // 2
                painter.drawRoundedRect(x, y, w, h, 2, 2)

class PlusButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Прикрепить файл")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        icon = QIcon("assets/icons/plus.svg")
        pixmap = icon.pixmap(18, 18)

        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2

        painter.drawPixmap(x, y, pixmap)

        """
        Не используется: 
        pen = QPen(QColor("#666666"), 2)
        painter.setPen(pen)
        cx, cy = self.width() // 2, self.height() // 2
        painter.drawLine(cx, cy - 8, cx, cy + 8)
        painter.drawLine(cx - 8, cy, cx + 8, cy)
        """

class SettingsButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        #self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Настройки")

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        icon = QIcon("assets/icons/settings.svg")
        pixmap = icon.pixmap(18, 18)

        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2

        painter.drawPixmap(x, y, pixmap)
        """
        Не используется:
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)

        painter.setPen(QColor("#666666"))
        painter.drawText(self.rect(), Qt.AlignCenter, "⚙")
        """  


class ChatUI(QMainWindow):
    send_message = Signal(str, list)
    settings_saved = Signal(dict)
    clear_history = Signal()
    stop_requested = Signal()
    

    def __init__(self, config, parent=None):
        super().__init__(parent)

        self.setWindowTitle("AI Ассистент")
        self.setMinimumSize(800, 600)
        self.config = config

        central_widget = QWidget()
        central_widget.setAcceptDrops(True)
        self.setCentralWidget(central_widget)

        central_widget.setAcceptDrops(True)
        central_widget.installEventFilter(self)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Драг энд дроп
        #self.setAcceptDrops(True)

        # Область сообщений
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(8, 12, 8, 12)
        self.messages_layout.setSpacing(4)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Панель вложений
        self.attachment_bar = AttachmentBar()
        self.attachment_bar.setVisible(False)
        main_layout.addWidget(self.attachment_bar)

        # Блок ввода
        self._create_input_area(main_layout)

        # Статус-бар
        self._create_statusbar()

        self._apply_styles()
        self.image_viewer = ImageViewer(self)
        self.image_viewer.hide()

    # ---------------------------------------------------------

    def _create_input_area(self, parent_layout):
        input_wrapper = QWidget()
        input_wrapper.setObjectName("inputWrapper")

        outer = QVBoxLayout(input_wrapper)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(0)

        input_container = QWidget()
        input_container.setObjectName("inputContainer")

        row = QHBoxLayout(input_container)
        row.setContentsMargins(8, 4, 4, 4)
        row.setSpacing(4)

        self.message_input = MessageInput()
        self.message_input.imagePasted.connect(self.on_image_pasted)
        self.message_input.setObjectName("messageInput")
        self.message_input.sendRequested.connect(self._on_send_requested)
        self.message_input.textChanged2.connect(self._on_text_changed)
        row.addWidget(self.message_input, stretch=1)

        self.attach_button = PlusButton()
        self.attach_button.setObjectName("attachBtn")
        self.attach_button.clicked.connect(self._on_attach_clicked)
        row.addWidget(self.attach_button)

        self.settings_button = SettingsButton()
        self.settings_button.setObjectName("settingsBtn")
        self.settings_button.clicked.connect(self._on_settings_clicked)
        row.addWidget(self.settings_button)

        self.smart_button = SmartButton()

        self.smart_button = SmartButton()
        self.smart_button.setObjectName("smartBtn")
        self.smart_button.clicked.connect(self._on_smart_clicked)
        row.addWidget(self.smart_button)

        outer.addWidget(input_container)
        parent_layout.addWidget(input_wrapper)

    # ---------------------------------------------------------

    def _create_statusbar(self):
        status_widget = QWidget()
        status_widget.setObjectName("statusBar")
        status_widget.setFixedHeight(24)

        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(12, 0, 12, 0)

        self.status_label = QLabel("Готов")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.message_counter = QLabel("Сообщений: 0")
        self.message_counter.setObjectName("statusLabel")
        layout.addWidget(self.message_counter)

        self.centralWidget().layout().addWidget(status_widget)

    # ---------------------------------------------------------

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #f7f7f8; color: #111111; }

            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cccccc;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #aaaaaa; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

            QWidget#inputWrapper {
                background-color: #ffffff;
                border-top: 1px solid #e5e5e5;
            }
            QWidget#inputContainer {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
            QTextEdit#messageInput {
                background: transparent;
                border: none;
                color: #111111;
                font-size: 14px;
                padding: 4px 0;
            }
            QPushButton#attachBtn {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton#attachBtn:hover { background-color: #e0e0e0; }

            QPushButton#settingsBtn {
                background: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton#settingsBtn:hover { background-color: #e0e0e0; }

            QPushButton#smartBtn {
                background-color: #e0e0e0;
                border: none;
                border-radius: 10px;
            }
            QPushButton#smartBtn:hover { background-color: #d0d0d0; }
            QPushButton#smartBtn[sendMode="true"] { background-color: #2563eb; }
            QPushButton#smartBtn[sendMode="true"]:hover { background-color: #1d4ed8; }
            QPushButton#smartBtn[stopMode="true"] { background-color: #dc2626; }
            QPushButton#smartBtn[stopMode="true"]:hover { background-color: #b91c1c; }
            QPushButton#smartBtn:disabled { background-color: #e0e0e0; }

            QWidget#statusBar {
                background-color: #f7f7f8;
                border-top: 1px solid #e5e5e5;
            }
            QLabel#statusLabel { color: #999999; font-size: 11px; background: transparent; }
        """)

    # ---------------------------------------------------------

    def _on_text_changed(self, has_text: bool):
        self.smart_button.setSendMode(has_text)
        self.smart_button.setProperty("sendMode", "true" if has_text else "false")
        self.smart_button.style().unpolish(self.smart_button)
        self.smart_button.style().polish(self.smart_button)

    def _on_smart_clicked(self):
        if self.smart_button._mode == "stop":
            self.stop_requested.emit()
        elif self.message_input.message():
            self._on_send_requested()
        else:
            self.setStatus("🎤 Запись голоса (скоро...)", 2000)

    def _on_send_requested(self):
        text = self.message_input.message()
        attachments = self.attachment_bar.attachments()
        if not text and not attachments:
            return
        # Передаём вложения в карточку чтобы показать их в диалоге
        self.addMessage("user", text, attachments=attachments)
        self.send_message.emit(text, attachments)
        self.message_input.clearMessage()
        self.attachment_bar.clear()

    def _on_attach_clicked(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы", "",
            "Все файлы (*.*);;Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        for path in file_paths:
            
            self.attachment_bar.addAttachment(path)

    def on_image_pasted(self, image):
        from pathlib import Path
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        from datetime import datetime
        filename = datetime.now().strftime("paste_%Y%m%d_%H%M%S_%f.png")
        path = temp_dir / filename
        image.save(str(path))
        self.attachment_bar.addAttachment(str(path))

    # ---------------------------------------------------------

    def addMessage(self, role: str, text: str, attachments: list = None):
        self.messages_layout.takeAt(self.messages_layout.count() - 1)
        card = MessageCard(role, text, attachments=attachments)
        card.imageClicked.connect(self.showImage)
        card.fileClicked.connect(self.openFile)
        self.messages_layout.addWidget(card)
        self.messages_layout.addStretch()
        self.message_counter.setText(f"Сообщений: {self.getMessageCount()}")
        self.scroll_to_bottom()
        return card

    def updateLastMessage(self, text: str):
        count = self.messages_layout.count()
        if count < 2:
            return
        last_widget = self.messages_layout.itemAt(count - 2).widget()
        if isinstance(last_widget, MessageCard):
            last_widget.setText(text)
        self.scroll_to_bottom()

    def appendToLastMessage(self, text: str):
        count = self.messages_layout.count()
        if count < 2:
            return
        last_widget = self.messages_layout.itemAt(count - 2).widget()
        if isinstance(last_widget, MessageCard):
            last_widget.appendText(text)
        self.scroll_to_bottom()

    def clearMessages(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if self.messages_layout.count() == 0:
            self.messages_layout.addStretch()
        self.message_counter.setText("Сообщений: 0")
        self.attachment_bar.clear()

    def getMessageCount(self) -> int:
        return self.messages_layout.count() - 1

    def getAllMessages(self) -> list:
        messages = []
        for i in range(self.messages_layout.count() - 1):
            widget = self.messages_layout.itemAt(i).widget()
            if isinstance(widget, MessageCard):
                messages.append({"role": widget.role, "text": widget.markdown()})
        return messages

    def setStatus(self, text: str, duration: int = 3000):
        self.status_label.setText(text)
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.status_label.setText("Готов"))

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def setSendEnabled(self, enabled: bool):
        # Ввод никогда не блокируем — пользователь может набирать следующее
        self.setStatus("Готов" if enabled else "Ожидание ответа...", 0 if not enabled else 1)

    def setStopMode(self, enabled: bool):
        self.smart_button.setStopMode(enabled)
        # Обновляем QSS цвет кнопки
        self.smart_button.setProperty("stopMode", "true" if enabled else "false")
        self.smart_button.style().unpolish(self.smart_button)
        self.smart_button.style().polish(self.smart_button)

    def getInputText(self) -> str:
        return self.message_input.message()

    def setInputText(self, text: str):
        self.message_input.setPlainText(text)

    def focusInput(self):
        self.message_input.setFocus()

    def closeEvent(self, event):
        print("closeEvent called")
        event.accept()

    def showImage(self, path):
        self.image_viewer.setGeometry(self.centralWidget().geometry())
        self.image_viewer.showImage(path)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.image_viewer.isVisible():
             self.image_viewer.setGeometry(self.rect())
    def openFile(self, path):
        
        if not os.path.exists(path):
            QMessageBox.warning(
                self,
                "Файл не найден",
                path
            )
            return

        os.startfile(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):

        for url in event.mimeData().urls():

            if url.isLocalFile():

                path = url.toLocalFile()

                self.attachment_bar.addAttachment(path)

        event.acceptProposedAction()

    def eventFilter(self, obj, event):

        if event.type() == QEvent.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True

        elif event.type() == QEvent.Drop:
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    self.attachment_bar.addAttachment(url.toLocalFile())

            event.acceptProposedAction()
            return True

        return super().eventFilter(obj, event)
    
    def _on_settings_clicked(self):
        # 1. Вытаскиваем текущие значения прямо из твоего словаря self.config
        current_url = self.config.get("api_url", "http://127.0.0.1:1234/v1")
        current_key = self.config.get("api_key", "")

        # 2. Показываем наш диалог (не забудь импортировать SettingsDialog, если вынес его в отдельный файл)
        dialog = SettingsDialog(current_url, current_key, self)
        
        if dialog.exec() == QDialog.Accepted:
            new_values = dialog.get_values()
            
            # 3. Обновляем текущий словарь конфигурации в UI
            self.config.update(new_values)
            
            # 4. Импортируем (если еще не импортировано в ui.py) и вызываем сохранение в файл
            from config import save_config
            save_config(self.config)
            
            # 5. Пинаем сигнал наружу (в main.py), если какому-то бэкенду/клиенту нужно 
            # на лету пересоздать сессию с новым ключом или URL
            self.settings_saved.emit(self.config)
            
            self.setStatus("⚙️ Настройки сохранены в config.json", 2000)