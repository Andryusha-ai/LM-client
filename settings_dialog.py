# settings_dialog.py
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTabWidget, QComboBox, QTextEdit,
    QMessageBox
)
from pathlib import Path
import json


class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.current_config = current_config.copy()
        self.setWindowTitle("Настройки")
        self.resize(750, 600)
        self.setMinimumSize(650, 550)

        # Убираем стандартные кнопки и заголовок
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowFlag(Qt.FramelessWindowHint)

        # Фон как у основной программы
        self.setStyleSheet("""
            QDialog {
                background-color: #f7f7f8;
                border-radius: 12px;
                border: 1px solid #e5e5e5;
            }
            QTabWidget::pane {
                background: transparent;
                border: none;
                margin-top: 8px;
            }
            QTabBar::tab {
                background: transparent;
                padding: 8px 16px;
                margin-right: 4px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 13px;
                font-weight: 500;
                color: #666666;
            }
            QTabBar::tab:selected {
                color: #111111;
                border-bottom: 2px solid #2563eb;
            }
            QTabBar::tab:hover:!selected {
                color: #111111;
                background: #f0f0f0;
                border-radius: 6px 6px 0 0;
            }
        """)

        # Основной контейнер
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 16, 24, 20)
        main_layout.setSpacing(12)

        # Заголовок
        title = QLabel("⚙️ Настройки")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #111111;
                padding-bottom: 4px;
                background: transparent;
            }
        """)
        main_layout.addWidget(title)

        # === Панель пресетов (сверху, над вкладками) ===
        presets_panel = QWidget()
        presets_panel.setStyleSheet("background: transparent;")
        presets_layout = QHBoxLayout(presets_panel)
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(8)

        # Метка
        preset_label = QLabel("Пресет:")
        preset_label.setStyleSheet("color: #444444; font-size: 13px; font-weight: 500; background: transparent;")
        presets_layout.addWidget(preset_label)

        # Выбор пресета
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(36)
        self.preset_combo.setMinimumWidth(200)
        self.preset_combo.setStyleSheet("""
            QComboBox {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 13px;
                color: #111111;
            }
            QComboBox:hover {
                border-color: #bbbbbb;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                subcontrol-position: right;
                subcontrol-origin: padding;
            }
            QComboBox::down-arrow {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #2563eb;
                color: #ffffff;
            }
        """)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        presets_layout.addWidget(self.preset_combo, stretch=1)

        # Кнопка обновить список пресетов
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setToolTip("Обновить список пресетов")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
            QPushButton:pressed {
                background: #d0d0d0;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_presets)
        presets_layout.addWidget(refresh_btn)

        # Поле для имени нового пресета
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText("Имя нового пресета...")
        self.preset_name_input.setMinimumHeight(36)
        self.preset_name_input.setMinimumWidth(150)
        self.preset_name_input.setEnabled(False)
        self.preset_name_input.setStyleSheet("""
            QLineEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 13px;
                color: #111111;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background: #ffffff;
            }
            QLineEdit:disabled {
                background: #e8e8e8;
                color: #999999;
            }
        """)
        presets_layout.addWidget(self.preset_name_input)

        main_layout.addWidget(presets_panel)

        # Создаём вкладки
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget {
                background: transparent;
                border: none;
            }
        """)

        # === Вкладка "Конфигурация" ===
        self._setup_config_tab()

        # === Вкладка "Персона" ===
        self._setup_persona_tab()

        main_layout.addWidget(self.tab_widget)

        # === Кнопки внизу ===
        self._setup_buttons(main_layout)

        self.setLayout(main_layout)

        # Инициализация папок
        self.personas_dir = Path("personas")
        self.personas_dir.mkdir(exist_ok=True)

        self.presets_dir = Path("config/presets")
        self.presets_dir.mkdir(parents=True, exist_ok=True)

        # Загружаем списки
        self._load_personas()
        self._load_presets()

        # Загружаем текущие значения
        self._load_current_values()

        # Фокус на поле URL
        self.api_url_input.setFocus()

    def _setup_config_tab(self):
        """Настройка вкладки 'Конфигурация'"""
        config_tab = QWidget()
        config_tab.setStyleSheet("background: transparent;")
        config_layout = QVBoxLayout(config_tab)
        config_layout.setSpacing(12)
        config_layout.setContentsMargins(0, 8, 0, 0)

        # API URL
        url_label = QLabel("API URL")
        url_label.setStyleSheet("color: #444444; font-size: 13px; font-weight: 500; background: transparent;")
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("http://127.0.0.1:1234/v1/chat/completions")
        self.api_url_input.setMinimumHeight(40)
        self.api_url_input.setStyleSheet("""
            QLineEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                color: #111111;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background: #ffffff;
            }
        """)
        config_layout.addWidget(url_label)
        config_layout.addWidget(self.api_url_input)

        # API Ключ
        key_label = QLabel("API Ключ")
        key_label.setStyleSheet("color: #444444; font-size: 13px; font-weight: 500; background: transparent;")

        key_container = QWidget()
        key_container.setStyleSheet("background: transparent;")
        key_layout = QHBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(8)

        # Модель
        model_label = QLabel("Модель")
        model_label.setStyleSheet("color: #444444; font-size: 13px; font-weight: 500; background: transparent;")
        config_layout.addWidget(model_label)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("openrouter/free")
        self.model_input.setMinimumHeight(40)
        self.model_input.setStyleSheet("""
            QLineEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                color: #111111;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background: #ffffff;
            }
        """)
        config_layout.addWidget(self.model_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Введите API ключ (если требуется)")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMinimumHeight(40)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                color: #111111;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background: #ffffff;
            }
        """)
        key_layout.addWidget(self.api_key_input, stretch=1)

        self.show_key_btn = QPushButton("👁")
        self.show_key_btn.setFixedSize(40, 40)
        self.show_key_btn.setCursor(Qt.PointingHandCursor)
        self.show_key_btn.setToolTip("Показать/скрыть ключ")
        self.show_key_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
            QPushButton:pressed {
                background: #d0d0d0;
            }
        """)
        self.show_key_btn.clicked.connect(self._toggle_key_visibility)
        key_layout.addWidget(self.show_key_btn)

        config_layout.addWidget(key_label)
        config_layout.addWidget(key_container)
        config_layout.addStretch()

        self.tab_widget.addTab(config_tab, "Конфигурация")

    def _setup_persona_tab(self):
        """Настройка вкладки 'Персона'"""
        persona_tab = QWidget()
        persona_tab.setStyleSheet("background: transparent;")
        persona_layout = QVBoxLayout(persona_tab)
        persona_layout.setSpacing(12)
        persona_layout.setContentsMargins(0, 8, 0, 0)

        # Описание
        desc_label = QLabel("Выберите личность для ассистента")
        desc_label.setStyleSheet("color: #666666; font-size: 13px; background: transparent;")
        persona_layout.addWidget(desc_label)

        # Выбор персоны + кнопки
        persona_select_layout = QHBoxLayout()
        persona_select_layout.setSpacing(8)

        self.persona_combo = QComboBox()
        self.persona_combo.setMinimumHeight(40)
        self.persona_combo.setStyleSheet("""
            QComboBox {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 14px;
                color: #111111;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: #bbbbbb;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                subcontrol-position: right;
                subcontrol-origin: padding;
            }
            QComboBox::down-arrow {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #2563eb;
                color: #ffffff;
            }
        """)
        self.persona_combo.currentTextChanged.connect(self._on_persona_changed)
        persona_select_layout.addWidget(self.persona_combo, stretch=1)

        # Кнопка обновить список персон
        refresh_personas_btn = QPushButton("🔄")
        refresh_personas_btn.setFixedSize(40, 40)
        refresh_personas_btn.setCursor(Qt.PointingHandCursor)
        refresh_personas_btn.setToolTip("Обновить список персон")
        refresh_personas_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
            QPushButton:pressed {
                background: #d0d0d0;
            }
        """)
        refresh_personas_btn.clicked.connect(self._refresh_personas)
        persona_select_layout.addWidget(refresh_personas_btn)

        # Кнопка редактировать
        self.edit_persona_btn = QPushButton("✏️")
        self.edit_persona_btn.setFixedSize(40, 40)
        self.edit_persona_btn.setCursor(Qt.PointingHandCursor)
        self.edit_persona_btn.setToolTip("Редактировать описание личности")
        self.edit_persona_btn.setEnabled(False)
        self.edit_persona_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #dbeafe;
                border-color: #2563eb;
            }
            QPushButton:pressed {
                background: #bfdbfe;
            }
            QPushButton:disabled {
                background: #e8e8e8;
                color: #999999;
            }
        """)
        self.edit_persona_btn.clicked.connect(self._edit_persona)
        persona_select_layout.addWidget(self.edit_persona_btn)

        # Кнопка удалить
        self.delete_persona_btn = QPushButton("🗑")
        self.delete_persona_btn.setFixedSize(40, 40)
        self.delete_persona_btn.setCursor(Qt.PointingHandCursor)
        self.delete_persona_btn.setToolTip("Удалить выбранную личность")
        self.delete_persona_btn.setEnabled(False)
        self.delete_persona_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #fee2e2;
                border-color: #dc2626;
            }
            QPushButton:pressed {
                background: #fecaca;
            }
            QPushButton:disabled {
                background: #e8e8e8;
                color: #999999;
            }
        """)
        self.delete_persona_btn.clicked.connect(self._delete_persona)
        persona_select_layout.addWidget(self.delete_persona_btn)

        persona_layout.addLayout(persona_select_layout)

        # Поле "Имя личности"
        name_label = QLabel("Имя личности:")
        name_label.setStyleSheet("color: #444444; font-size: 13px; font-weight: 500; background: transparent; margin-top: 4px;")
        persona_layout.addWidget(name_label)

        self.persona_name_input = QLineEdit()
        self.persona_name_input.setPlaceholderText("Введите имя для новой личности...")
        self.persona_name_input.setMinimumHeight(40)
        self.persona_name_input.setEnabled(False)
        self.persona_name_input.setStyleSheet("""
            QLineEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                color: #111111;
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background: #ffffff;
            }
            QLineEdit:disabled {
                background: #e8e8e8;
                color: #999999;
            }
        """)
        persona_layout.addWidget(self.persona_name_input)

        # Поле "Описание личности"
        desc_label2 = QLabel("Описание личности:")
        desc_label2.setStyleSheet("color: #444444; font-size: 13px; font-weight: 500; background: transparent; margin-top: 4px;")
        persona_layout.addWidget(desc_label2)

        self.preview_text = QTextEdit()
        self.preview_text.setMinimumHeight(120)
        self.preview_text.setEnabled(False)
        self.preview_text.setStyleSheet("""
            QTextEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                color: #333333;
            }
            QTextEdit:focus {
                border: 2px solid #2563eb;
                background: #ffffff;
            }
            QTextEdit:disabled {
                background: #e8e8e8;
                color: #999999;
            }
        """)
        persona_layout.addWidget(self.preview_text)

        persona_layout.addStretch()

        self.tab_widget.addTab(persona_tab, "Персона")

    def _setup_buttons(self, main_layout):
        """Настройка кнопок внизу"""
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background: transparent;")
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedWidth(100)
        cancel_btn.setFixedHeight(40)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                color: #555555;
            }
            QPushButton:hover {
                background: #f0f0f0;
                border-color: #bbbbbb;
            }
            QPushButton:pressed {
                background: #e5e5e5;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self.save_button = QPushButton("💾 Сохранить")
        self.save_button.setFixedWidth(120)
        self.save_button.setFixedHeight(40)
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                color: #ffffff;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
            QPushButton:pressed {
                background: #1e40af;
            }
        """)
        self.save_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.save_button)

        main_layout.addWidget(buttons_widget)

    # ---------------------------------------------------------
    # Методы управления пресетами
    # ---------------------------------------------------------

    def _load_presets(self):
        """Загрузка списка пресетов"""
        current = self.preset_combo.currentText() if self.preset_combo.count() > 0 else ""
        self.preset_combo.clear()

        preset_files = list(self.presets_dir.glob("*.json"))
        for file in sorted(preset_files):
            self.preset_combo.addItem(file.stem)

        self.preset_combo.addItem("➕ Новый пресет")

        if current:
            index = self.preset_combo.findText(current)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)

    def _refresh_presets(self):
        """Обновить список пресетов"""
        self._load_presets()

    def _on_preset_changed(self, text):
        """Обработка смены пресета"""
        is_new = text == "➕ Новый пресет"
        is_preset = text and text != "➕ Новый пресет"

        self.preset_name_input.setEnabled(is_new)

        if is_preset:
            preset_file = self.presets_dir / f"{text}.json"
            if preset_file.exists():
                try:
                    with open(preset_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.api_url_input.setText(data.get("api_url", ""))
                        self.api_key_input.setText(data.get("api_key", ""))
                        self.model_input.setText(data.get("model", "openrouter/free"))
                        persona = data.get("persona", "Без личности")
                        index = self.persona_combo.findText(persona)
                        if index >= 0:
                            self.persona_combo.setCurrentIndex(index)
                except Exception:
                    pass
        elif is_new:
            self.preset_name_input.setText("")
            self.preset_name_input.setFocus()
        else:
            self.preset_name_input.setText("")

    def _save_current_as_preset(self):
        """Сохранение текущих настроек как пресет"""
        current_preset = self.preset_combo.currentText()
        current_data = {
            "api_url": self.api_url_input.text().strip(),
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_input.text().strip(),
            "persona": self.persona_combo.currentText()
        }
        if current_data["persona"] == "➕ Новая личность":
            persona_name = self.persona_name_input.text().strip()
            if persona_name:
                current_data["persona"] = persona_name
        name = self.preset_name_input.text().strip()
        if current_preset and current_preset != "➕ Новый пресет":
            preset_file = self.presets_dir / f"{current_preset}.json"
            if preset_file.exists():
                try:
                    with open(preset_file, "r", encoding="utf-8") as f:
                        saved_data = json.load(f)
                        # Сравниваем текущие настройки с сохранёнными
                        if (saved_data.get("api_url", "") == current_data["api_url"] and
                            saved_data.get("api_key", "") == current_data["api_key"] and
                            saved_data.get("model", "") == current_data["model"] and
                            saved_data.get("persona", "") == current_data["persona"]):
                            # Ничего не изменилось — сохранять не нужно
                            return
                except Exception:
                    pass

            reply = QMessageBox.question(
                self,
                "Обновить пресет",
                f"Обновить пресет '{name}' текущими настройками?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        else:
            if not name:
                QMessageBox.warning(self, "Ошибка", "Введите имя пресета")
                return

        preset_data = {
            "name": name,
            "api_url": self.api_url_input.text().strip(),
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_input.text().strip(), 
            "persona": self.persona_combo.currentText()
        }

        if preset_data["persona"] == "➕ Новая личность":
            persona_name = self.persona_name_input.text().strip()
            if persona_name:
                preset_data["persona"] = persona_name

        try:
            preset_file = self.presets_dir / f"{name}.json"
            with open(preset_file, "w", encoding="utf-8") as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)

            self.current_config["current_preset"] = name

            self._load_presets()
            index = self.preset_combo.findText(name)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)

            QMessageBox.information(
                self,
                "Сохранено",
                f"Пресет '{name}' сохранён."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить пресет: {e}"
            )

    def accept(self):
        """Переопределяем accept для сохранения пресета"""
        self._save_current_as_preset()
        super().accept()

    # ---------------------------------------------------------
    # Методы управления персонами
    # ---------------------------------------------------------

    def _toggle_key_visibility(self):
        """Переключение видимости ключа"""
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText("🙈")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText("👁")

    def _load_personas(self):
        """Загрузка существующих персон в комбобокс"""
        current = self.persona_combo.currentText() if self.persona_combo.count() > 0 else ""
        self.persona_combo.clear()
        self.persona_combo.addItem("Без личности")
        persona_files = list(self.personas_dir.glob("*.txt"))
        for file in sorted(persona_files):
            self.persona_combo.addItem(file.stem)
        self.persona_combo.addItem("➕ Новая личность")
        if current:
            index = self.persona_combo.findText(current)
            if index >= 0:
                self.persona_combo.setCurrentIndex(index)
            else:
                self.persona_combo.setCurrentIndex(0)

    def _refresh_personas(self):
        """Обновить список персон"""
        self._load_personas()
        self._on_persona_changed(self.persona_combo.currentText())

    def _on_persona_changed(self, text):
        """Обработка смены персоны"""
        if text == "➕ Новая личность":
            self.persona_name_input.setEnabled(True)
            self.preview_text.setEnabled(True)
            self.preview_text.setPlainText("")
            self.persona_name_input.setFocus()
            self.edit_persona_btn.setEnabled(False)
            self.delete_persona_btn.setEnabled(False)
        else:
            self.persona_name_input.setEnabled(False)
            self.persona_name_input.setText("")

            is_existing = text not in ("Без личности", "")
            self.edit_persona_btn.setEnabled(is_existing)
            self.delete_persona_btn.setEnabled(is_existing)

            if is_existing:
                self.preview_text.setEnabled(False)
                self._load_persona_preview(text)
            else:
                self.preview_text.setEnabled(False)
                self.preview_text.setPlainText("")

    def _load_persona_preview(self, persona_name: str):
        """Загрузка текста персоны для предпросмотра"""
        if not persona_name or persona_name == "Без личности":
            self.preview_text.setPlainText("")
            return
        file_path = self.personas_dir / f"{persona_name}.txt"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.preview_text.setPlainText(f.read())
            except Exception as e:
                self.preview_text.setPlainText(f"Ошибка загрузки: {e}")
        else:
            self.preview_text.setPlainText("Файл не найден")

    def _edit_persona(self):
        """Редактирование описания личности"""
        current = self.persona_combo.currentText()
        if not current or current in ("Без личности", "➕ Новая личность"):
            return

        self.preview_text.setEnabled(True)
        self.preview_text.setFocus()

        self.edit_persona_btn.setText("💾")
        self.edit_persona_btn.setToolTip("Сохранить изменения")
        self.edit_persona_btn.clicked.disconnect()
        self.edit_persona_btn.clicked.connect(self._save_persona_edit)

        self.persona_combo.setEnabled(False)
        self.delete_persona_btn.setEnabled(False)

        self.preview_text.setStyleSheet("""
            QTextEdit {
                background: #ffffff;
                border: 2px solid #2563eb;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                color: #333333;
            }
        """)

    def _save_persona_edit(self):
        """Сохранение изменений в описании личности"""
        current = self.persona_combo.currentText()
        if not current or current in ("Без личности", "➕ Новая личность"):
            return

        file_path = self.personas_dir / f"{current}.txt"
        content = self.preview_text.toPlainText().strip()

        if not content:
            content = f"# Личность: {current}\n\nОпишите здесь характер и манеру общения этой личности."

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self._exit_edit_mode()
            QMessageBox.information(
                self,
                "Сохранено",
                f"Изменения для '{current}' сохранены."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить: {e}"
            )

    def _exit_edit_mode(self):
        """Выход из режима редактирования"""
        self.edit_persona_btn.setText("✏️")
        self.edit_persona_btn.setToolTip("Редактировать описание личности")
        self.edit_persona_btn.clicked.disconnect()
        self.edit_persona_btn.clicked.connect(self._edit_persona)

        self.persona_combo.setEnabled(True)
        self.preview_text.setEnabled(False)

        self.preview_text.setStyleSheet("""
            QTextEdit {
                background: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                color: #333333;
            }
            QTextEdit:disabled {
                background: #e8e8e8;
                color: #999999;
            }
        """)

        current = self.persona_combo.currentText()
        if current and current not in ("Без личности", "➕ Новая личность"):
            self._load_persona_preview(current)

        self.delete_persona_btn.setEnabled(current not in ("Без личности", "➕ Новая личность", ""))

    def _delete_persona(self):
        """Удаление персоны"""
        current = self.persona_combo.currentText()
        if not current or current in ("Без личности", "➕ Новая личность"):
            QMessageBox.information(self, "Нельзя удалить", "Выберите конкретную личность для удаления.")
            return

        file_path = self.personas_dir / f"{current}.txt"
        if not file_path.exists():
            QMessageBox.warning(self, "Не найден", f"Файл '{current}.txt' не найден.")
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить личность '{current}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                file_path.unlink()
                self._refresh_personas()
                QMessageBox.information(self, "Удалено", f"Личность '{current}' удалена.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {e}")

    def _load_current_values(self):
        """Загрузка текущих значений из конфига"""
        current_preset = self.current_config.get("current_preset", "")
        if current_preset:
            preset_file = self.presets_dir / f"{current_preset}.json"
            self.preset_name_input.setText(current_preset)
            self.preset_name_input.setEnabled(False)
            if preset_file.exists():
                try:
                    with open(preset_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.api_url_input.setText(data.get("api_url", ""))
                        self.api_key_input.setText(data.get("api_key", ""))
                        persona = data.get("persona", "Без личности")
                        index = self.persona_combo.findText(persona)
                        if index >= 0:
                            self.persona_combo.setCurrentIndex(index)
                            self._load_persona_preview(persona)
                        preset_index = self.preset_combo.findText(current_preset)
                        if preset_index >= 0:
                            self.preset_combo.setCurrentIndex(preset_index)
                    return
                except Exception:
                    pass

        self.api_url_input.setText(self.current_config.get("api_url", ""))
        self.api_key_input.setText(self.current_config.get("api_key", ""))
        self.model_input.setText(self.current_config.get("model", "openrouter/free"))

        persona = self.current_config.get("persona", "Без личности")
        if persona and persona != "Без личности":
            index = self.persona_combo.findText(persona)
            if index >= 0:
                self.persona_combo.setCurrentIndex(index)
                self._load_persona_preview(persona)
            else:
                self.persona_combo.setCurrentIndex(0)
        else:
            self.persona_combo.setCurrentIndex(0)

    def keyPressEvent(self, event):
        """Обработка клавиш"""
        if event.key() == Qt.Key_Escape:
            if self.edit_persona_btn.text() == "💾":
                self._exit_edit_mode()
                return
            if self.preset_name_input.isEnabled() and self.preset_name_input.hasFocus():
                self.preset_name_input.setText("")
                return
        super().keyPressEvent(event)

    def get_values(self):
        """Получение значений из диалога"""
        persona = self.persona_combo.currentText()
        if persona == "➕ Новая личность":
            name = self.persona_name_input.text().strip()
            if name:
                file_path = self.personas_dir / f"{name}.txt"
                content = self.preview_text.toPlainText().strip()
                if not content:
                    content = f"# Личность: {name}\n\nОпишите здесь характер и манеру общения этой личности."
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                persona = name
            else:
                persona = "Без личности"

        return {
            "api_url": self.api_url_input.text().strip(),
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_input.text().strip(),
            "persona": persona,
            "current_preset": self.preset_combo.currentText() if self.preset_combo.currentText() != "➕ Новый пресет" else ""
        }