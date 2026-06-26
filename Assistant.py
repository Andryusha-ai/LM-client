# assistant.py
from ui import ChatUI
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatUI()
    window.show()
    
    # Обработка отправки сообщения
    def on_send(text, attachments):
        print(f"Отправлено: {text}")
        print(f"Вложения: {attachments}")
        
        # Имитация ответа с задержкой
        window.setSendEnabled(False)
        
        # Добавляем сообщение ассистента
        QTimer.singleShot(500, lambda: window.addMessage("assistant", "Думаю..."))
        
        # Имитация стриминга
        response = "Привет! Я ассистент на основе Qwen 9B VLM. "
        response += "Чем я могу вам помочь сегодня?"
        
        # Стримим по буквам
        def stream_response():
            current_text = ""
            for char in response:
                current_text += char
                window.updateLastMessage(current_text)
                QTimer.singleShot(30, lambda: None)  # маленькая задержка
                # Используем QTimer для имитации задержки
                QTimer.singleShot(30, lambda c=current_text: window.updateLastMessage(c))
        
        # Упрощенная имитация стриминга
        current_text = ""
        def stream_step():
            nonlocal current_text
            if len(current_text) < len(response):
                current_text = response[:len(current_text) + 1]
                window.updateLastMessage(current_text)
                QTimer.singleShot(30, stream_step)
            else:
                window.setSendEnabled(True)
        
        QTimer.singleShot(1000, stream_step)
    
    window.send_message.connect(on_send)
    
    sys.exit(app.exec())