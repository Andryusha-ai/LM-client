import os
import json
import uuid
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QScrollArea, QLineEdit)
from PySide6.QtCore import Qt, Signal

class LeftBar(QWidget):
    chat_deleted = Signal(str)
    """Левая панель для отображения списка чатов"""
    
    def __init__(self, history_dir="history", parent=None):
        super().__init__(parent)
        
        # ВАЖНО: не используем self.parent — это встроенный метод QWidget,
        # его перезапись сломает работу Qt (например, widget.parent() в других местах кода)
        self.main_window = parent
        
        # Файл текущего выбранного чата и ссылки на кнопки списка (для подсветки)
        self.current_chat_file = None
        self.chat_buttons = {}
        
        # Создаем папку history, если её нет (относительно директории AI)
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.history_dir = os.path.join(base_path, history_dir)
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
            
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 20, 10, 20)
        self.layout.setSpacing(5)
        
        # Стиль для левой панели (светлая тема)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #1a1a1a;
                font-family: 'Segoe UI', sans-serif;
            }
        """)

        # --- 1. Кнопка "Новый чат" ---
        self.new_chat_btn = QPushButton("+ Новый чат")
        self.new_chat_btn.setMinimumHeight(50)
        self.new_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        self.new_chat_btn.clicked.connect(self.create_new_chat)
        self.layout.addWidget(self.new_chat_btn)

        # --- 2. Поиск по чатам ---
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Поиск по чатам...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #f2f2f5;
                color: #1a1a1a;
                border: 1px solid #dcdce0;
                border-radius: 10px;
                padding: 10px 15px;
                font-size: 14px;
            }
        """)
        self.search_bar.textChanged.connect(self.refresh_chat_list)
        self.layout.addWidget(self.search_bar)

        # --- 3. Скролл-зона для списка чатов ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #ffffff;
            }
        """)
        
        self.chat_list_container = QWidget()
        self.chat_list_layout = QVBoxLayout(self.chat_list_container)
        self.chat_list_layout.setSpacing(3)
        self.chat_list_layout.setContentsMargins(0, 10, 0, 10)
        
        self.scroll_area.setWidget(self.chat_list_container)
        self.layout.addWidget(self.scroll_area)

        # Принудительно обновляем размер виджета
        self.chat_list_container.setFixedWidth(280)

        # Обновляем список при запуске
        self.refresh_chat_list()

    def create_new_chat(self):
        """Создает новый чат"""
        chat_id = str(uuid.uuid4())[:12]
        current_time = datetime.now()
        timestamp = current_time.strftime("%H:%M")
        
        # Название файла (берем из последнего имени для отображения)
        default_title = f"Чат {timestamp}"
        
        file_name = f"{chat_id}.json"
        full_file_path = os.path.join(self.history_dir, file_name)
        
        # Создаем файл с базовой структурой чата
        chat_data = {
            "id": chat_id,
            "title": default_title,
            "timestamp": timestamp,
            "messages": []  # Пустой список сообщений для нового чата
        }
        
        try:
            with open(full_file_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Создан новый чат: {file_name}")
            
            # Обновляем список, чтобы новый чат сразу появился в сайдбаре
            self.refresh_chat_list()
            
            # Переключаемся на новый чат
            self.on_chat_selected(file_name)
            
        except Exception as e:
            print(f"❌ Ошибка при создании чата: {e}")

    def refresh_chat_list(self, search_filter=None):
        """Обновляет список чатов"""
        # Полностью очищаем layout, включая сами виджеты (иначе они остаются в памяти)
        while self.chat_list_layout.count():
            item = self.chat_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.chat_buttons = {}

        files = [f for f in os.listdir(self.history_dir) if f.endswith('.json')]
        if not files:
            return

        # Сортируем по дате изменения (новые сверху)
        files.sort(
            key=lambda x: os.path.getmtime(os.path.join(self.history_dir, x)),
            reverse=True
        )

        search_filter = (search_filter or "").strip().lower()
        current_time = datetime.now()
        last_group = None

        for file in files:
            full_file_path = os.path.join(self.history_dir, file)

            try:
                with open(full_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                title = data.get("title", file.replace(".json", ""))
                timestamp_str = data.get("timestamp", "—")

                # Применяем фильтр поиска по названию чата
                if search_filter and search_filter not in title.lower():
                    continue

                # Определяем группу по дате изменения файла и вставляем
                # заголовок группы, если она сменилась
                file_mtime = datetime.fromtimestamp(os.path.getmtime(full_file_path))
                group = self.get_date_group(file_mtime, current_time)
                if group != last_group:
                    self.add_date_grouping_label(group)
                    last_group = group

                # Добавляем иконку и текст
                btn = QPushButton(f"💬 {title}")

                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, fname=file: self._show_context_menu(btn, fname)
                )

                btn.clicked.connect(lambda checked, fname=file: self.on_chat_selected(fname))

                btn.setText(f"{title}  \t\t{timestamp_str}")

                btn.setMinimumHeight(45)
                is_selected = (file == self.current_chat_file)
                btn.setStyleSheet(self._chat_button_style(is_selected))

                btn.clicked.connect(lambda checked, fname=file: self.on_chat_selected(fname))

                self.chat_list_layout.addWidget(btn)
                self.chat_buttons[file] = btn

            except Exception as e:
                print(f"Ошибка при чтении {file}: {e}")

        # Весь лишний вертикальный простор уходит сюда, а не в плашку даты
        # (у QLabel по умолчанию растягивающаяся политика размера, у QPushButton — нет)
        self.chat_list_layout.addStretch()

    def _chat_button_style(self, selected: bool) -> str:
        """Стиль кнопки чата: обычный или подсвеченный (текущий открытый чат)"""
        if selected:
            return """
                QPushButton {
                    text-align: left;
                    padding: 10px 15px;
                    border-radius: 8px;
                    background-color: rgba(79, 70, 229, 0.14);
                    border: 1px solid rgba(79, 70, 229, 0.45);
                    color: #1a1a1a;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(79, 70, 229, 0.18);
                }
            """
        return """
            QPushButton {
                text-align: left;
                padding: 10px 15px;
                border-radius: 8px;
                background-color: transparent;
                border: 1px solid transparent;
                color: #1a1a1a;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(79, 70, 229, 0.12);
                border: 1px solid rgba(79, 70, 229, 0.3);
            }
        """

    def get_date_group(self, file_time, current_time):
        """Определяет, к какой группе (Сегодня/Вчера/...) относится файл по дате изменения"""
        file_date = file_time.date()
        today = current_time.date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        if file_date == today:
            return "Сегодня"
        elif file_date == yesterday:
            return "Вчера"
        elif file_date >= week_ago:
            return "7 дн. назад"
        else:
            return "30 дн. назад"

    def add_date_grouping_label(self, label_text):
        """Добавляет разделитель-заголовок группы дат в список чатов"""
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                padding: 4px 6px;
                font-size: 11px;
                font-weight: bold;
                color: #9a9aa5;
            }
        """)
        self.chat_list_layout.addWidget(label)

    def rename_chat(self, filename: str, new_title: str):
        """
        Переименовывает чат: обновляет поле "title" в JSON-файле истории
        и текст соответствующей кнопки в сайдбаре (без перестройки всего списка).
        """
        full_file_path = os.path.join(self.history_dir, filename)

        try:
            with open(full_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['title'] = new_title

            with open(full_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Ошибка при переименовании чата {filename}: {e}")
            return

        btn = self.chat_buttons.get(filename)
        if btn is not None:
            timestamp_str = data.get("timestamp", "—")
            btn.setText(f"{new_title}  \t\t{timestamp_str}")

    def on_chat_selected(self, filename):
        """Вызывается при выборе чата"""
        print(f"Выбран чат: {filename}")

        # Подсвечиваем выбранный чат в списке и снимаем подсветку с предыдущего
        previous_file = self.current_chat_file
        self.current_chat_file = filename

        if previous_file in self.chat_buttons:
            self.chat_buttons[previous_file].setStyleSheet(self._chat_button_style(False))
        if filename in self.chat_buttons:
            self.chat_buttons[filename].setStyleSheet(self._chat_button_style(True))

        if self.main_window is None:
            return
        if hasattr(self.main_window, 'switch_to_chat'):
            self.main_window.switch_to_chat(filename)
        elif hasattr(self.main_window, 'chat_manager'):
            self.main_window.chat_manager.load_chat(filename)

    def delete_chat(self, filename: str):
        """Удаляет чат: удаляет файл и убирает кнопку из списка"""
        if not filename:
            return

        full_path = os.path.join(self.history_dir, filename)
    
        # Удаляем файл
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"🗑 Чат удалён: {filename}")
        except Exception as e:
            print(f"❌ Ошибка при удалении файла {filename}: {e}")
            return

        # Убираем кнопку из словаря
        if filename in self.chat_buttons:
            btn = self.chat_buttons.pop(filename)
            btn.deleteLater()

        # Убираем из layout
        for i in range(self.chat_list_layout.count()):
            item = self.chat_list_layout.itemAt(i)
            if item and item.widget() and item.widget() is btn:
                self.chat_list_layout.takeAt(i)
                break

        # Если удалили текущий чат — сбрасываем
        if self.current_chat_file == filename:
            self.current_chat_file = None
            # Снимаем подсветку со всех кнопок
            for btn in self.chat_buttons.values():
                btn.setStyleSheet(self._chat_button_style(False))

        # Посылаем сигнал наружу (в Assistant.py)
        self.chat_deleted.emit(filename)

        # Перестраиваем список (чтобы обновить группы дат)
        # Но можно просто обновить, если нужно
        self.refresh_chat_list()

    def _show_context_menu(self, btn, filename):
        """Показывает контекстное меню при ПКМ на чате"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
    
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #dcdce0;
                border-radius: 8px;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f0f0f5;
            }
        """)
    
        delete_action = menu.addAction("🗑 Удалить чат")
        delete_action.triggered.connect(lambda: self.delete_chat(filename))
        # x = btn.x() + btn.width() // 2 - 40
        # y = btn.y() + btn.height()
        # global_pos = self.chat_list_container.mapToGlobal(btn.pos() + btn.rect().bottomLeft())
        menu.exec(QCursor.pos())