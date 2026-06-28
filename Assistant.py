# assistant.py
import sys
import logging
import traceback
import requests
import base64
from ui import ChatUI
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, Signal, QObject
from pathlib import Path
from cache_manager import CacheManager
from config import load_config, save_config

MODEL_NAME = "local-model"
CacheManager.init()
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "error_log.txt"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8"
)

def excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error(
        "Критическая ошибка:\n" + "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = excepthook


def image_to_data_url(path):
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif",
        "webp": "image/webp", "bmp": "image/bmp",
    }.get(suffix, "image/png")
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


class LMWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, messages, config):
        super().__init__()
        self.config = config
        self.messages = messages
        self._cancelled = False
        self._session = requests.Session()

    def cancel(self):
        print("cancel", id(self))
        self._cancelled = True
        try:
            self._session.close()  # закрывает сокет, прерывает запрос
        except Exception:
            pass

    def run(self):
        print("run", id(self))
        try:
            response = self._session.post(
                self.config['api_url'],
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                json={
                    "model": MODEL_NAME,
                    "messages": self.messages,
                    "stream": False,
                },
                timeout=120,
            )
            if self._cancelled:
                return
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            print("cancelled =", self._cancelled)
            if not self._cancelled:
                print("emit", id(self), self._cancelled)
                self.finished.emit(text)
        except requests.exceptions.ConnectionError:
            if not self._cancelled:
                self.error.emit("Не удалось подключиться — проверь API URL")
        except requests.exceptions.Timeout:
            if not self._cancelled:
                self.error.emit("Превышено время ожидания ответа от модели")
        except requests.exceptions.HTTPError as e:
            if not self._cancelled:
                status = e.response.status_code if e.response is not None else "?"
                if status == 401:
                    self.error.emit("Неверный API ключ (401)")
                elif status == 404:
                    self.error.emit("API URL не найден (404) — проверь адрес")
                else:
                    self.error.emit(f"Ошибка сервера ({status})")
        except KeyError:
            if not self._cancelled:
                self.error.emit("Неожиданный ответ от модели — возможно модель не загружена")
        except Exception as e:
            logging.error(f"Неизвестная ошибка: {type(e).__name__}: {str(e)}", exc_info=True)
            if not self._cancelled:
                self.error.emit("Неизвестная ошибка — данные в папке \\logs")


class App(QObject):

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.history = []
        self.thread = None
        self.worker = None
        self.dot_timer = QTimer()
        self.dot_timer.timeout.connect(self._animate_dots)
        self.dot_state = 0
        self._typing = False
        self._stop_typing = False

        self.window = ChatUI(self.config)
        self.window.send_message.connect(self.on_send)
        self.window.settings_saved.connect(self.on_settings_saved)
        self.window.stop_requested.connect(self.on_stop)
        self.window.show()

    def _animate_dots(self):
        dots = "." * (self.dot_state % 4 + 1)
        self.window.updateLastMessage(dots)
        self.dot_state += 1

    def _stop_thread(self):
        """Останавливаем поток без wait — просто сигнализируем о завершении"""
        try:
            print("worker =", self.worker)
            print("thread =", self.thread)
            if self.worker is not None:
                self.worker.cancel()
            if self.thread is not None:
                self.thread.quit()
        except RuntimeError:
            pass
        #self.thread = None
        #self.worker = None

    def on_stop(self):
        print("on_stop called, typing=", self._typing)
        if self._typing:
            self._stop_typing = True
            self.window.setStopMode(False)
        else:
            print("1")
            self.dot_timer.stop()
            print("2")
            #self._stop_thread()
            print("3")
            self.window.updateLastMessage("Прервано")
            print("4")
            self.window.setStopMode(False)
            print("5")

    def on_send(self, text, attachments):
        # Прерываем текущее если что-то идёт
        if self._typing:
            self._stop_typing = True
        self.dot_timer.stop()
        self._stop_thread()

        content = [{"type": "text", "text": text}]

        IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        TEXT_EXTENSIONS = {
            ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".xml",
            ".ini", ".cfg", ".js", ".ts", ".cpp", ".c", ".h", ".cs", ".java"
        }

        for path in attachments:
            suffix = Path(path).suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_to_data_url(path)}
                })
            elif suffix in TEXT_EXTENSIONS:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        file_text = f.read()
                    content.append({
                        "type": "text",
                        "text": f"Файл {Path(path).name}:\n```{suffix[1:]}\n{file_text}\n```"
                    })
                except Exception as e:
                    logging.error(f"Не удалось прочитать файл {path}: {e}")

        self.history.append({"role": "user", "content": content})

        self.window.addMessage("assistant", ".")
        self.dot_state = 0
        self.dot_timer.start(400)
        self.window.setStopMode(True)

        self.thread = QThread()
        self.worker = LMWorker(self.history.copy(), self.config)
        self.worker.moveToThread(self.thread)

        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_finished(self, response_text):
        self.dot_timer.stop()
        # Не вызываем wait() — просто quit и обнуляем
        #try:
            #if self.thread is not None:
                #self.thread.quit()
        #except RuntimeError:
            #pass
        #self.thread = None
        #self.worker = None

        self.history.append({"role": "assistant", "content": response_text})

        self._current_text = ""
        self._full_text = response_text
        self._typing = True
        self._stop_typing = False
        self._type_step()

    def _type_step(self):
        if self._stop_typing:
            self._typing = False
            self._stop_typing = False
            self.window.setStopMode(False)
            return

        if len(self._current_text) < len(self._full_text):
            self._current_text = self._full_text[:len(self._current_text) + 1]
            self.window.updateLastMessage(self._current_text)
            QTimer.singleShot(15, self._type_step)
        else:
            self._typing = False
            self.window.setStopMode(False)

    def on_error(self, error_text):
        self.dot_timer.stop()
        try:
            if self.thread is not None:
                self.thread.quit()
        except RuntimeError:
            pass
        self.thread = None
        self.worker = None
        self.window.updateLastMessage(f"Ошибка: {error_text}")
        self.window.setStopMode(False)

    def on_settings_saved(self, new_config):
        self.config = new_config


if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = App()
    sys.exit(app.exec())
