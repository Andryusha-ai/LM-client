from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import sys


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("LM Assistant")
        self.resize(1000, 700)

        self.attachments = []

        # ---------- Центральный виджет ----------

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)

        # ---------- История ----------

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)

        root.addWidget(self.chat)

        # ---------- Вложения ----------

        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(90)

        root.addWidget(self.attachments_list)

        # ---------- Нижняя панель ----------

        bottom = QHBoxLayout()

        self.attach_button = QPushButton("📎")
        self.attach_button.setFixedWidth(40)

        bottom.addWidget(self.attach_button)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Введите сообщение...")

        bottom.addWidget(self.input)

        self.send_button = QPushButton("🎤")
        self.send_button.setFixedWidth(50)

        bottom.addWidget(self.send_button)

        root.addLayout(bottom)

        # ---------- Сигналы ----------

        self.input.textChanged.connect(self.update_send_button)
        self.input.returnPressed.connect(self.send_message)

        self.send_button.clicked.connect(self.send_message)
        self.attach_button.clicked.connect(self.add_attachment)

    # =====================================================

    def update_send_button(self):

        if self.input.text().strip():
            self.send_button.setText("➤")
        else:
            self.send_button.setText("🎤")

    # =====================================================

    def add_attachment(self):

        files, _ = QFileDialog.getOpenFileNames(self)

        for file in files:
            self.attachments.append(file)

            item = QListWidgetItem(file)
            self.attachments_list.addItem(item)

    # =====================================================

    def send_message(self):

        text = self.input.text().strip()

        if not text:

            print("TODO: запись голоса")

            return

        self.chat.append(f"<b>Ты:</b> {text}<br>")

        self.input.clear()

        # Заглушка

        self.chat.append("<b>Ассистент:</b> Пока не подключён.<br>")

        self.attachments.clear()
        self.attachments_list.clear()


# =========================================================


def run():

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())