# assistant.py
import sys
import re
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
from datetime import datetime

#MODEL_NAME = "deepseek-v4-flash"
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

# Заголовок вида "Чат HH:MM" — так называет новый чат LeftBar.create_new_chat.
# Пока название чата не менялось (совпадает с этим шаблоном), после первого
# сообщения пользователя генерируем осмысленный заголовок через модель.
DEFAULT_CHAT_TITLE_RE = re.compile(r'^Чат \d{2}:\d{2}$')


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
            model_name = self.config.get("model", "openrouter/free")
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
       
            # Отправляем запрос в стрим-режиме.
            # User-Agent по умолчанию у requests ("python-requests/x.x.x")
            # часто прилетает под антибот-правила WAF перед API (это и даёт
            # "Access denied by security policy" ещё до самого OpenRouter).
            # HTTP-Referer/X-Title — заголовки, которые OpenRouter сам
            # рекомендует слать для идентификации приложения.
            self._response = self._session.post(
                self.config['api_url'],
                headers={
                    "Authorization": f"Bearer {self.config['api_key']}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; LocalChatAssistant/1.0)",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "Local Chat Assistant",
                },
                json={
                    "model": model_name,  
                    "messages": messages,
                    "stream": True,
                },
                stream=True,
                timeout=120,
            )
            
            # Проверяем статус до чтения стрима
            if self._response.status_code != 200:
                self._handle_http_error(self._response.status_code, self._response)
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
                self._handle_http_error(status, e.response)
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

    def _handle_http_error(self, status, response=None):
        """Обработка HTTP ошибок"""
        detail = ""
        if response is not None:
            try:
                body = response.json()
                # OpenRouter (и большинство OpenAI-совместимых API) кладут
                # текст причины в error.message
                detail = ""
                if isinstance(body, dict):
                    err = body.get("error")
                    if isinstance(err, dict):
                        detail = err.get("message", "")
                if not detail:
                    detail = json.dumps(body, ensure_ascii=False)[:500]
            except Exception:
                try:
                    detail = response.text[:500]
                except Exception:
                    detail = ""

            if detail:
                logging.error(f"HTTP {status} от API: {detail}")

        if status == 401:
            msg = "Неверный API ключ (401)"
        elif status == 404:
            msg = "API URL не найден (404) — проверь адрес"
        elif status == 403:
            msg = "Доступ запрещён (403)"
        else:
            msg = f"Ошибка сервера ({status})"

        if detail:
            msg += f": {detail}"

        self.error.emit(msg)

    def on_chat_deleted(self, filename):
        """Обработка удаления чата"""
        if filename == self.current_chat_file:
            self.current_chat_file = None
            self._clear_chat()
            self.window.set_input_enabled(False)
            self.window.setStatus("Чат удалён. Выберите другой или создайте новый.")

class TitleWorker(QObject):
    """
    Отдельный лёгкий запрос (без стрима) для генерации короткого заголовка чата
    на основе первого сообщения пользователя.
    """
    title_received = Signal(str)
    error = Signal(str)

    def __init__(self, user_text, config):
        super().__init__()
        self.user_text = user_text
        self.config = config

    def run(self):
        try:
            model_name = self.config.get("model", "openrouter/free")
            
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; LocalChatAssistant/1.0)",
                "HTTP-Referer": "https://localhost",
                "X-Title": "Local Chat Assistant",
            }
            
            # ✅ Жёстко требуем короткий ответ БЕЗ размышлений
            prompt = (
                f"/no_think ОТВЕТЬ ТОЛЬКО ОДНИМ ПРЕДЛОЖЕНИЕМ ДО 5 СЛОВ. НЕ РАЗМЫШЛЯЙ. НЕ ПИШИ 'Думаю'.\n\n"
                f"Тема сообщения пользователя:\n{self.user_text}\n\n"
                f"Тема:"
            )
            
            # ✅ Добавляем system, который запрещает reasoning
            messages = [
                {"role": "system", "content": "Ты — помощник, который даёт только короткие фактические ответы без объяснений. Не используй мыслительный процесс."},
                {"role": "user", "content": prompt}
            ]

            response = requests.post(
                self.config['api_url'],
                headers=headers,
                json={
                    "model": model_name,
                    "messages": messages,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "stream": False,
                    # "max_tokens": 150,  # ✅ даём достаточно токенов, чтобы модель успела закончить мысль
                    "temperature": 0.1,
                },
                timeout=150,
            )

            if response.status_code != 200:
                self.error.emit(f"HTTP {response.status_code}: {response.text[:200]}")
                return

            data = response.json()
            
            # ✅ Пытаемся достать content
            content = ""
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                content = msg.get("content", "") or msg.get("reasoning_content", "")
            
            # ✅ Если это reasoning — вырезаем всё до первого ответа
            if content:
                # Если в ответе есть "Thinking process" — пытаемся найти фразу после неё
                if "Thinking process" in content or "**" in content:
                    # Ищем строку, которая начинается с "- Тема:" или просто не содержит спецсимволов
                    lines = content.split("\n")
                    for line in lines:
                        line = line.strip()
                        # Ищем осмысленную строку
                        if line and not line.startswith("**") and not line.startswith("*") and not line.startswith("1."):
                            content = line
                            break
                    
                    # Если ничего не нашли — берём последнюю строку
                    if not content or "Thinking process" in content:
                        for line in reversed(lines):
                            line = line.strip()
                            if line and len(line) > 3:
                                content = line
                                break

            # ✅ Убираем мусор
            if content:
                # Убираем "Тема:" в начале
                content = re.sub(r'^Тема:\s*', '', content)
                # Убираем кавычки
                content = content.strip().strip('"\'«»')
                # Если слишком длинное — обрезаем
                if len(content) > 60:
                    content = content[:60] + "..."
                
                if content and len(content) > 2:
                    self.title_received.emit(content)
                    return

            # ✅ Если всё сломалось — последняя попытка: берём первые 5 слов из пользовательского сообщения
            fallback = " ".join(self.user_text.split()[:5])
            if fallback:
                self.title_received.emit(fallback + "...")
            else:
                self.error.emit("Не удалось сгенерировать заголовок")

        except requests.exceptions.Timeout:
            self.error.emit("Таймаут при генерации заголовка")
        except Exception as e:
            logging.error(f"Ошибка генерации заголовка: {type(e).__name__}: {str(e)}", exc_info=True)
            self.error.emit(str(e))

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


        # Файл текущего открытого чата (устанавливается при выборе/создании чата в сайдбаре)
        self.current_chat_file = None
        # Активные фоновые запросы генерации заголовка — храним ссылки,
        # чтобы поток/воркер не были собраны сборщиком мусора до завершения
        self._title_jobs = []

        self.window = ChatUI(self.config)
        self.window.send_message.connect(self.on_send)
        self.window.settings_saved.connect(self.on_settings_saved)
        self.window.stop_requested.connect(self.on_stop)
        self.window.chat_selected.connect(self.on_chat_selected)
        self.window.show()
        self.window.left_bar.chat_deleted.connect(self.on_chat_deleted)

    def on_chat_selected(self, filename):
        """
        Пользователь выбрал (или создал) чат в сайдбаре.
        NB: здесь только запоминается, какой файл сейчас активен — этого
        достаточно для переименования заголовка. Подгрузка самой истории
        сообщений из файла в окно чата — отдельная задача, сюда не входит.
        """
        self.current_chat_file = filename
        self.window.set_input_enabled(bool(filename))
        if filename:
            self._load_chat(filename)  # ← загружаем чат
        else:
            self._clear_chat()         # ← очищаем, если чат не выбран

    def _get_chat_title(self, filename):
        """Читает текущий title чата напрямую из его JSON-файла в history/"""
        if not filename:
            return None
        full_path = Path(self.window.left_bar.history_dir) / filename
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("title")
        except Exception as e:
            logging.error(f"Не удалось прочитать title чата {filename}: {e}")
            return None

    def _maybe_generate_title(self, text, filename):
        """Если у чата ещё дефолтный заголовок ('Чат HH:MM'), запускает генерацию нового"""
        if not text.strip() or not filename:
            return

        current_title = self._get_chat_title(filename)
        if not current_title or not DEFAULT_CHAT_TITLE_RE.match(current_title):
            return

        self._start_title_generation(text, filename)

    def _start_title_generation(self, text, filename):
        thread = QThread()
        worker = TitleWorker(text, self.config)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        worker.title_received.connect(lambda title, fn=filename: self._on_title_generated(fn, title))
        worker.error.connect(self._on_title_error)

        # Каноничная Qt-цепочка остановки/очистки потока-воркера.
        # ВАЖНО: раньше здесь был отдельный _cleanup(), который сам вызывал
        # thread.quit() + thread.wait() — но _cleanup был обычной функцией
        # (не слотом QObject), поэтому Qt подключал её напрямую (direct
        # connection) и выполнял в том же фоновом потоке, где работал воркер.
        # thread.wait(), вызванный потоком САМ НА СЕБЯ, и давал
        # "QThread::wait: Thread tried to wait on itself" — Qt просто
        # игнорировал ожидание, поток мог не выгружаться корректно.
        # Правильно — доверить остановку сигналам, без ручного wait():
        worker.title_received.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        job = (thread, worker)
        self._title_jobs.append(job)
        thread.finished.connect(lambda: self._title_jobs.remove(job) if job in self._title_jobs else None)

        thread.start()

    def _on_title_generated(self, filename, title):
        print(f"✅ Заголовок чата обновлён: {title}")
        self.window.left_bar.rename_chat(filename, title)

    def _on_title_error(self, message):
        # Раньше это шло только в logs/error_log.txt и было не видно в консоли
        print(f"⚠️ Не удалось сгенерировать заголовок чата: {message}")
        logging.error(f"Генерация заголовка чата не удалась: {message}")

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
        self._save_chat()
        # Если у текущего чата ещё дефолтное название ("Чат HH:MM") — запускаем
        # фоновую генерацию короткого заголовка по первому сообщению пользователя.
        # Идёт параллельно с основной генерацией, чтобы не задерживать ответ.
        # self._maybe_generate_title(text, self.current_chat_file)

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
            self._save_chat()
        
        self._is_typing = False
        self._current_response = ""
        self._full_response = ""
        if self.current_chat_file:
            current_title = self._get_chat_title(self.current_chat_file)
            if current_title and DEFAULT_CHAT_TITLE_RE.match(current_title):
                self._start_title_generation(self.history[-2]["content"], self.current_chat_file)

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

    def _save_chat(self):
        """Сохраняет текущую историю в файл чата"""
        if not self.current_chat_file:
            return
    
        # Если история пустая — не сохраняем
        if not self.history:
            return
    
        full_path = Path(self.window.left_bar.history_dir) / self.current_chat_file
        full_path.parent.mkdir(parents=True, exist_ok=True)
    
        try:
            # Читаем существующий файл, чтобы не потерять title и другие поля
            if full_path.exists():
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        
            # Обновляем историю и время последнего изменения
            data["messages"] = self.history
            data["updated"] = datetime.now().isoformat()
        
            # Если нет title — ставим дефолтный
            if "title" not in data or not data["title"]:
                data["title"] = f"Чат {datetime.now().strftime('%H:%M')}"
        
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Чат сохранён: {self.current_chat_file}")
        
        except Exception as e:
            logging.error(f"Не удалось сохранить чат {self.current_chat_file}: {e}")

    def _load_chat(self, filename):
        """Загружает чат из файла"""
        if not filename:
            self._clear_chat()
            return
    
        full_path = Path(self.window.left_bar.history_dir) / filename
        if not full_path.exists():
            self._clear_chat()
            return
    
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._clear_chat()

            # ✅ history → messages
            self.history = data.get("messages", [])
        
            # Загружаем в UI
            for msg in self.history:
                role = msg.get("role", "assistant")
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Если content — список (вложения), пытаемся извлечь текст
                    text = ""
                    for part in content:
                        if part.get("type") == "text":
                            text = part.get("text", "")
                            break
                    content = text
                self.window.addMessage(role, content)
        
            print(f"📂 Чат загружен: {filename}, сообщений: {len(self.history)}")
        
        except Exception as e:
            logging.error(f"Не удалось загрузить чат {filename}: {e}")

    def _clear_chat(self):
        """Очищает окно чата и историю"""
        self.window.clearMessages()
        self.history = []

    def on_chat_deleted(self, filename):
        """Обработка удаления чата"""
        print(f"🗑 Сигнал удаления получен: {filename}")
    
        if filename == self.current_chat_file:
            self.current_chat_file = None
            self._clear_chat()
            self.window.set_input_enabled(False)
            self.window.setStatus("Чат удалён. Выберите другой или создайте новый.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = App()
    sys.exit(app.exec())