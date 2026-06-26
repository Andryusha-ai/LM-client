# ui.py
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QStatusBar,
    QSizePolicy,
    QLabel,
    QProgressBar,
    QComboBox,
    QCheckBox,
)

from widgets.message_card import MessageCard
from widgets.message_input import MessageInput
from widgets.attachment_bar import AttachmentBar


class ChatUI(QMainWindow):
    send_message = Signal(str, list)
    clear_history = Signal()
    save_chat = Signal()
    load_chat = Signal()
    settings_requested = Signal()
    model_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("AI Ассистент")
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self._create_toolbar()

        # Область сообщений
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # Панель вложений
        self.attachment_bar = AttachmentBar()
        self.attachment_bar.setVisible(False)
        main_layout.addWidget(self.attachment_bar)

        # Блок ввода
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.message_input = MessageInput()
        self.message_input.sendRequested.connect(self._on_send_requested)
        input_layout.addWidget(self.message_input, stretch=1)

        self.attach_button = QPushButton("📎")
        self.attach_button.setFixedSize(40, 40)
        self.attach_button.setToolTip("Прикрепить файл")
        self.attach_button.clicked.connect(self._on_attach_clicked)
        input_layout.addWidget(self.attach_button)

        self.send_button = QPushButton("➤")
        self.send_button.setFixedSize(40, 40)
        self.send_button.setToolTip("Отправить (Enter)")
        self.send_button.clicked.connect(self._on_send_requested)
        input_layout.addWidget(self.send_button)

        main_layout.addLayout(input_layout)

        # Статус-бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.status_label = QLabel("Готов")
        self.statusBar.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setMaximumHeight(20)
        self.statusBar.addPermanentWidget(self.progress_bar)

        self.message_counter = QLabel("Сообщений: 0")
        self.statusBar.addPermanentWidget(self.message_counter)

        self._apply_styles()

    # ---------------------------------------------------------

    def _create_toolbar(self):
        toolbar = QToolBar("Главная панель")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        clear_action = QAction("🗑 Очистить", self)
        clear_action.setToolTip("Очистить историю чата")
        clear_action.triggered.connect(self._on_clear_clicked)
        toolbar.addAction(clear_action)

        toolbar.addSeparator()

        save_action = QAction("💾 Сохранить", self)
        save_action.setToolTip("Сохранить чат в файл")
        save_action.triggered.connect(self.save_chat.emit)
        toolbar.addAction(save_action)

        load_action = QAction("📂 Загрузить", self)
        load_action.setToolTip("Загрузить чат из файла")
        load_action.triggered.connect(self.load_chat.emit)
        toolbar.addAction(load_action)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Модель: "))

        self.model_selector = QComboBox()
        self.model_selector.setMinimumWidth(150)
        self.model_selector.addItems([
            "Qwen 9B VLM",
            "Qwen 7B",
            "Llama 3.2",
            "Другая..."
        ])
        self.model_selector.currentTextChanged.connect(self.model_changed.emit)
        toolbar.addWidget(self.model_selector)

        toolbar.addSeparator()

        settings_action = QAction("⚙ Настройки", self)
        settings_action.setToolTip("Открыть настройки")
        settings_action.triggered.connect(self.settings_requested.emit)
        toolbar.addAction(settings_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        self.dev_mode_check = QCheckBox("Dev")
        self.dev_mode_check.setToolTip("Режим разработчика")
        toolbar.addWidget(self.dev_mode_check)

    # ---------------------------------------------------------

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; }
            QToolBar {
                background-color: #2a2a2a;
                border: none;
                padding: 4px;
                spacing: 8px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QToolBar QToolButton:hover { background-color: #3a3a3a; }
            QToolBar QToolButton:pressed { background-color: #4a4a4a; }
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e0e0e0;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #e0e0e0;
                selection-background-color: #3a3a3a;
            }
            QCheckBox { color: #e0e0e0; }
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                color: #e0e0e0;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #4a4a4a; }
            QPushButton:disabled { opacity: 0.5; }
            QStatusBar {
                background-color: #2a2a2a;
                color: #a0a0a0;
            }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #5a5a5a; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar:horizontal {
                background: #2a2a2a;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #4a4a4a;
                border-radius: 5px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover { background: #5a5a5a; }
        """)

    # ---------------------------------------------------------

    def _on_send_requested(self):
        text = self.message_input.message()
        attachments = self.attachment_bar.attachments()

        if not text and not attachments:
            return

        # Добавляем сообщение пользователя сразу в UI
        self.addMessage("user", text)
        
        # Эмитим сигнал для внешней обработки
        self.send_message.emit(text, attachments)

        # Очищаем поле ввода
        self.message_input.clearMessage()
        self.attachment_bar.clear()

    # ---------------------------------------------------------

    def _on_attach_clicked(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы для прикрепления",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;"
            "Все файлы (*.*)"
        )

        for path in file_paths:
            self.attachment_bar.addAttachment(path)

    # ---------------------------------------------------------

    def _on_clear_clicked(self):
        reply = QMessageBox.question(
            self,
            "Очистка чата",
            "Вы уверены, что хотите очистить всю историю сообщений?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.clear_history.emit()
            self.clearMessages()

    # ---------------------------------------------------------

    def addMessage(self, role: str, text: str):
        """Добавление сообщения в чат"""
        # Убираем старый стрейч
        self.messages_layout.takeAt(self.messages_layout.count() - 1)

        card = MessageCard(role, text)
        self.messages_layout.addWidget(card)

        # Добавляем новый стрейч
        self.messages_layout.addStretch()

        # Обновляем счетчик
        count = self.getMessageCount()
        self.message_counter.setText(f"Сообщений: {count}")

        # Прокручиваем вниз
        self.scroll_to_bottom()

        return card

    # ---------------------------------------------------------

    def updateLastMessage(self, text: str):
        """Обновление последнего сообщения (для стриминга)"""
        count = self.messages_layout.count()
        if count < 2:
            return

        last_widget = self.messages_layout.itemAt(count - 2).widget()

        if isinstance(last_widget, MessageCard):
            last_widget.setText(text)

        self.scroll_to_bottom()

    # ---------------------------------------------------------

    def appendToLastMessage(self, text: str):
        """Добавление текста к последнему сообщению (для стриминга)"""
        count = self.messages_layout.count()
        if count < 2:
            return

        last_widget = self.messages_layout.itemAt(count - 2).widget()

        if isinstance(last_widget, MessageCard):
            last_widget.appendText(text)

        self.scroll_to_bottom()

    # ---------------------------------------------------------

    def clearMessages(self):
        """Очистка всех сообщений"""
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.messages_layout.count() == 0:
            self.messages_layout.addStretch()

        self.message_counter.setText("Сообщений: 0")
        self.attachment_bar.clear()

    # ---------------------------------------------------------

    def getMessageCount(self) -> int:
        return self.messages_layout.count() - 1

    # ---------------------------------------------------------

    def getAllMessages(self) -> list:
        messages = []
        for i in range(self.messages_layout.count() - 1):
            widget = self.messages_layout.itemAt(i).widget()
            if isinstance(widget, MessageCard):
                messages.append({
                    "role": widget.role,
                    "text": widget.markdown()
                })
        return messages

    # ---------------------------------------------------------

    def setStatus(self, text: str, duration: int = 3000):
        self.status_label.setText(text)
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.status_label.setText("Готов"))

    # ---------------------------------------------------------

    def setProgress(self, value: int, max_value: int = 100):
        if value < 0 or value > max_value:
            self.progress_bar.setVisible(False)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(max_value)
        self.progress_bar.setValue(value)

        if value == max_value:
            QTimer.singleShot(500, lambda: self.progress_bar.setVisible(False))

    # ---------------------------------------------------------

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    # ---------------------------------------------------------

    def setSendEnabled(self, enabled: bool):
        self.send_button.setEnabled(enabled)
        self.message_input.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)

        if enabled:
            self.setStatus("Готов")
        else:
            self.setStatus("Ожидание ответа...", 0)

    # ---------------------------------------------------------

    def getInputText(self) -> str:
        return self.message_input.message()

    # ---------------------------------------------------------

    def setInputText(self, text: str):
        self.message_input.setPlainText(text)

    # ---------------------------------------------------------

    def focusInput(self):
        self.message_input.setFocus()

    # ---------------------------------------------------------

    def closeEvent(self, event):
        event.accept()