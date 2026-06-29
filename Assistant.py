# assistant.py
import sys
import logging
import traceback
import requests
import base64
import json
from ui import ChatUI
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, Signal, QObject, QMutex, QWaitCondition
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
    chunk_received = Signal(str)  # каждый новый кусок текста
    finished = Signal()           # стрим завершён
    error = Signal(str)           # ошибка

    def __init__(self, messages, config):
        super().__init__()
        self.config = config
        self.messages = messages
        self._cancelled = False
        self._session = None
        self._response = None
        self._mutex = QMutex()
        self._cond = QWaitCondition()

    def cancel(self):
        """Безопасная отмена запроса"""
        self._mutex.lock()
        self._cancelled = True
        self._mutex.unlock()
        
        # Пробуждаем поток, если он ждёт
        self._cond.wakeAll()
        
        # Закрываем сессию, чтобы прервать чтение
        try:
            if self._response:
                self._response.close()
            if self._session:
                self._session.close()
        except Exception:
            pass

    def run(self):
        """Запуск стрим-запроса"""
        try:
            self._session = requests.Session()
            messages = self.messages.copy()
            persona = self.config.get("persona", "")  
            # Если выбрана персона, добавляем системный промпт
            if persona and persona != "Без личности":
                persona_path = Path("personas") / f"{persona}.txt"
                if persona_path.exists():
                    try:
                        with open(persona_path, "r", encoding="utf-8") as f:
                            system_prompt = f.read()
                            # Добавляем системное сообщение в начало
                            messages.insert(0, {"role": "system", "content": system_prompt})
                    except Exception:
                        pass   
       
            # Отправляем запрос в стрим-режиме
            self._response = self._session.post(
                self.config['api_url'],
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": True,
                },
                stream=True,
                timeout=120,
            )
            
            # Проверяем статус до чтения стрима
            if self._response.status_code != 200:
                self._handle_http_error(self._response.status_code)
                return
            
            # Читаем стрим
            for line in self._response.iter_lines(decode_unicode=False):  # ← меняем на False
                # Проверяем отмену
                self._mutex.lock()
                cancelled = self._cancelled
                self._mutex.unlock()
    
                if cancelled:
                    return
    
                if not line:
                    continue
    
                # Декодируем явно в UTF-8
                try:
                    line_str = line.decode('utf-8')
                except UnicodeDecodeError:
                    continue
    
                if not line_str.startswith("data: "):
                    continue
    
                # Парсим JSON
                data_str = line_str[6:]  # убираем "data: "
                if data_str == "[DONE]":
                    break
    
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
        
                    if content:
                        self.chunk_received.emit(content)
            
                except json.JSONDecodeError:
                    continue
            
            # Проверяем отмену перед финишем
            self._mutex.lock()
            cancelled = self._cancelled
            self._mutex.unlock()
            
            if not cancelled:
                self.finished.emit()
                
        except requests.exceptions.ConnectionError:
            if not self._cancelled:
                self.error.emit("Не удалось подключиться — проверь API URL")
        except requests.exceptions.Timeout:
            if not self._cancelled:
                self.error.emit("Превышено время ожидания ответа от модели")
        except requests.exceptions.HTTPError as e:
            if not self._cancelled:
                status = e.response.status_code if e.response is not None else "?"
                self._handle_http_error(status)
        except Exception as e:
            logging.error(f"Неизвестная ошибка: {type(e).__name__}: {str(e)}", exc_info=True)
            if not self._cancelled:
                self.error.emit("Неизвестная ошибка — данные в папке \\logs")
        finally:
            # Закрываем ресурсы
            try:
                if self._response:
                    self._response.close()
                if self._session:
                    self._session.close()
            except Exception:
                pass

    def _handle_http_error(self, status):
        """Обработка HTTP ошибок"""
        if status == 401:
            self.error.emit("Неверный API ключ (401)")
        elif status == 404:
            self.error.emit("API URL не найден (404) — проверь адрес")
        else:
            self.error.emit(f"Ошибка сервера ({status})")


class App(QObject):

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.history = []
        self.thread = None
        self.worker = None
        self._is_typing = False
        self._full_response = ""
        self._current_response = ""

        self.window = ChatUI(self.config)
        self.window.send_message.connect(self.on_send)
        self.window.settings_saved.connect(self.on_settings_saved)
        self.window.stop_requested.connect(self.on_stop)
        self.window.show()

    def _stop_thread(self):
        """Останавливаем текущий поток и очищаем ресурсы"""
        try:
            if self.worker is not None:
                self.worker.cancel()
                # Даём время на отмену
                QThread.msleep(100)
                
            if self.thread is not None:
                if self.thread.isRunning():
                    self.thread.quit()
                    if not self.thread.wait(1000):  # ждём до 1 сек
                        self.thread.terminate()
                        self.thread.wait()
                self.thread = None
                
            if self.worker is not None:
                self.worker.deleteLater()
                self.worker = None
                
        except Exception as e:
            logging.error(f"Ошибка остановки потока: {e}")

    def on_stop(self):
        """Обработка кнопки Stop"""
        if self._is_typing:
            # Во время печати - просто останавливаем печать
            self._is_typing = False
            self.window.setStopMode(False)
        else:
            # Во время запроса - прерываем стрим
            self._stop_thread()
            current_text = self.window.getLastMessage() 
            if current_text:
                self.window.updateLastMessage(f"{current_text} ⏹")
            else:
                self.window.updateLastMessage("⏹ Прервано")
            self.window.setStopMode(False)
            self._is_typing = False

    def on_send(self, text, attachments):
        # Останавливаем текущий запрос
        self._stop_thread()
        self._is_typing = False
        self._full_response = ""
        self._current_response = ""

        # Формируем контент
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

        # Показываем пустое сообщение для ответа
        self.window.addMessage("assistant", "")
        self.window.setStopMode(True)

        # Запускаем стрим
        self.thread = QThread()
        self.worker = LMWorker(self.history.copy(), self.config)
        self.worker.moveToThread(self.thread)

        self.worker.chunk_received.connect(self.on_chunk_received)
        self.worker.finished.connect(self.on_stream_finished)
        self.worker.error.connect(self.on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_chunk_received(self, chunk):
        """Получен новый кусок текста"""
        self._full_response += chunk
        self._current_response += chunk
        self.window.updateLastMessage(self._current_response)

    def on_stream_finished(self):
        """Стрим завершён успешно"""
        self._stop_thread()
        self.window.setStopMode(False)
        
        # Сохраняем в историю
        if self._full_response:
            self.history.append({"role": "assistant", "content": self._full_response})
        
        self._is_typing = False
        self._current_response = ""
        self._full_response = ""

    def on_error(self, error_text):
        """Ошибка в стриме"""
        self._stop_thread()
        self.window.updateLastMessage(f"❌ {error_text}")
        self.window.setStopMode(False)
        self._is_typing = False
        self._current_response = ""
        self._full_response = ""

    def on_settings_saved(self, new_config):
        self.config = new_config


if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = App()
    sys.exit(app.exec())