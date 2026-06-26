# assistant.py
import sys
import requests
from ui import ChatUI
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, Signal, QObject

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
API_KEY = "sk-lm-vZmTYDyw:kh9AZHdIMoeBbB78bw8s"
MODEL_NAME = "local-model"


class LMWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        try:
            response = requests.post(
                LM_STUDIO_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": MODEL_NAME,
                    "messages": self.messages,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {str(e)}")


class App(QObject):
    def __init__(self):
        super().__init__()
        self.history = []
        self.thread = None
        self.worker = None
        self.dot_timer = QTimer()
        self.dot_timer.timeout.connect(self._animate_dots)
        self.dot_state = 0

        self.window = ChatUI()
        self.window.send_message.connect(self.on_send)
        self.window.show()

    def _animate_dots(self):
        dots = "." * (self.dot_state % 4 + 1)
        self.window.updateLastMessage(dots)
        self.dot_state += 1

    def on_send(self, text, attachments):
        self.window.setSendEnabled(False)
        self.history.append({"role": "user", "content": text})

        self.window.addMessage("assistant", ".")
        self.dot_state = 0
        self.dot_timer.start(400)

        self.thread = QThread()
        self.worker = LMWorker(self.history.copy())
        self.worker.moveToThread(self.thread)

        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_finished(self, response_text):
        self.dot_timer.stop()
        self.thread.quit()
        self.thread.wait()

        self.history.append({"role": "assistant", "content": response_text})

        self._current_text = ""
        self._full_text = response_text
        self._type_step()

    def _type_step(self):
        if len(self._current_text) < len(self._full_text):
            self._current_text = self._full_text[:len(self._current_text) + 1]
            self.window.updateLastMessage(self._current_text)
            QTimer.singleShot(15, self._type_step)
        else:
            self.window.setSendEnabled(True)

    def on_error(self, error_text):
        self.dot_timer.stop()
        self.thread.quit()
        self.thread.wait()
        self.window.updateLastMessage(f"Ошибка: {error_text}")
        self.window.setSendEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = App()
    sys.exit(app.exec())
