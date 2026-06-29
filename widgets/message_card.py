# widgets/message_card.py
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QTextBrowser,
    QAbstractScrollArea,
)
from pathlib import Path
from datetime import datetime
import html
import re


class MessageCard(QFrame):
    """
    Карточка одного сообщения.
    role: "user" | "assistant" | "system"
    """

    imageClicked = Signal(str)
    fileClicked = Signal(str)

    def __init__(self, role: str, text: str = "", attachments: list = None, parent=None):
        super().__init__(parent)

        self.role = role
        self._attachments = attachments or []
        self._raw_text = text

        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(0)

        self.bubble = QFrame()
        self.bubble.setObjectName("bubble_user" if role == "user" else "bubble_assistant")
        self.bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 8)
        bubble_layout.setSpacing(6)

        # Вложения
        if self._attachments:
            for path in self._attachments:
                s = Path(path).suffix.lower()
                if s in {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}:
                    img_label = QLabel()
                    pix = QPixmap(path)
                    if not pix.isNull():
                        MAX_W = 260
                        MAX_H = 220
                        pix = pix.scaled(
                            MAX_W,
                            MAX_H,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        img_label.setPixmap(pix)
                        img_label.setCursor(Qt.PointingHandCursor)
                        img_label.mousePressEvent = (
                            lambda e, p=path: self.imageClicked.emit(p)
                        )
                        img_label.setFixedSize(pix.size())
                        img_label.setAlignment(Qt.AlignCenter)
                        bubble_layout.addWidget(img_label)
                else:
                    file_label = QLabel(f"📄 {Path(path).name}")
                    file_label.setCursor(Qt.PointingHandCursor)
                    file_label.mousePressEvent = (
                        lambda e, p=path: (print("CLICK", p), self.fileClicked.emit(p))
                    )

                    file_label.setStyleSheet("color: #555; font-size: 12px;")
                    bubble_layout.addWidget(file_label)

        # Текст через QTextBrowser с HTML — даёт word-break
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(True)
        self.text.setFrameShape(QFrame.NoFrame)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text.setHtml(self._markdown_to_html(text))

        bubble_layout.addWidget(self.text)

        # Время
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setObjectName("timeLabel")
        time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        time_label.setAlignment(Qt.AlignRight if role == "user" else Qt.AlignLeft)
        time_label.setStyleSheet("color: #aaaaaa; font-size: 11px; background: transparent;")
        bubble_layout.addWidget(time_label)

        if role == "user":
            outer.addStretch()
            outer.addWidget(self.bubble)
        else:
            outer.addWidget(self.bubble)
            outer.addStretch()

        self._apply_style()

    # --------------------------------------------------

    def _markdown_to_html(self, text: str) -> str:
        """Конвертирует Markdown в HTML"""
        if not text:
            return ""

        # Экранируем HTML, чтобы не сломать
        text = html.escape(text)

        # Заголовки
        text = re.sub(r'^### (.*?)$', r'<h3 style="font-size: 15px; font-weight: 600; margin: 8px 0 4px 0;">\1</h3>', text, flags=re.M)
        text = re.sub(r'^## (.*?)$', r'<h2 style="font-size: 17px; font-weight: 600; margin: 10px 0 6px 0;">\1</h2>', text, flags=re.M)
        text = re.sub(r'^# (.*?)$', r'<h1 style="font-size: 20px; font-weight: 700; margin: 12px 0 8px 0;">\1</h1>', text, flags=re.M)

        # Жирный
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

        # Курсив
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

        # Зачёркнутый
        text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)

        # Блок кода — показываем язык
        text = re.sub(
            r'```(\w*)\n(.*?)```',
            self._format_code_block,
            text,
            flags=re.DOTALL
        )

        # Код (инлайн)
        text = re.sub(r'`(.*?)`', r'<code style="background: #f0f0f0; padding: 1px 6px; border-radius: 4px; font-family: monospace; font-size: 13px;">\1</code>', text)

        # Блок кода
        text = re.sub(
            r'```(.*?)\n(.*?)```',
            r'<pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 8px; overflow-x: auto; font-family: monospace; font-size: 13px; margin: 8px 0;"><code>\2</code></pre>',
            text,
            flags=re.DOTALL
        )

        # Цитаты
        text = re.sub(r'^> (.*?)$', r'<blockquote style="border-left: 3px solid #2563eb; padding-left: 12px; margin: 6px 0; color: #555;">\1</blockquote>', text, flags=re.M)

        # Списки (маркированные)
        text = re.sub(r'^\- (.*?)$', r'<li style="margin-left: 20px;">\1</li>', text, flags=re.M)
        text = re.sub(r'^\* (.*?)$', r'<li style="margin-left: 20px;">\1</li>', text, flags=re.M)
        
        # Если есть список, оборачиваем в <ul>
        if '<li' in text:
            text = re.sub(r'(<li.*?</li>)', r'<ul style="margin: 4px 0; padding: 0;">\1</ul>', text, flags=re.DOTALL)

        # Нумерованные списки
        text = re.sub(r'^(\d+)\. (.*?)$', r'<li style="margin-left: 20px;">\2</li>', text, flags=re.M)
        if '<li' in text:
            text = re.sub(r'(<li.*?</li>)', r'<ol style="margin: 4px 0; padding: 0;">\1</ol>', text, flags=re.DOTALL)

        # Горизонтальная линия
        text = re.sub(r'^---$', r'<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 12px 0;">', text, flags=re.M)

        # Ссылки [текст](url)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color: #2563eb; text-decoration: none;">\1</a>', text)

        # Переносы строк
        text = text.replace('\n', '<br>')

        return f"""
        <html><body>
        <div style="
            font-size: 14px;
            color: #111111;
            word-wrap: break-word;
            white-space: normal;
            margin: 0; padding: 0;
            line-height: 1.6;
        ">{text}</div>
        </body></html>
        """

    # --------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        max_w = int(self.width() * 0.75)
        self.bubble.setMaximumWidth(max_w)
        bubble_w = self.bubble.width()
        if bubble_w > 0:
            self.text.document().setTextWidth(bubble_w - 28)
            self._fix_height()

    def _fix_height(self):
        h = int(self.text.document().size().height()) + 4
        self.text.setFixedHeight(max(h, 20))
        self.updateGeometry()

    # --------------------------------------------------

    def _apply_style(self):
        if self.role == "user":
            self.bubble.setStyleSheet("""
                QFrame#bubble_user {
                    background-color: #e8e8ea;
                    border-radius: 16px;
                    border-bottom-right-radius: 4px;
                }
            """)
        else:
            self.bubble.setStyleSheet("""
                QFrame#bubble_assistant {
                    background-color: #ffffff;
                    border-radius: 16px;
                    border-bottom-left-radius: 4px;
                    border: 1px solid #ebebeb;
                }
            """)

        self.text.setStyleSheet("""
            QTextBrowser {
                border: none;
                background: transparent;
                color: #111111;
            }
            QTextBrowser a {
                color: #2563eb;
                text-decoration: none;
            }
            QTextBrowser a:hover {
                text-decoration: underline;
            }
        """)

    # --------------------------------------------------

    def setText(self, text: str):
        self._raw_text = text
        self.text.setHtml(self._markdown_to_html(text))
        self._fix_height()

    def appendText(self, text: str):
        self._raw_text += text
        self.text.setHtml(self._markdown_to_html(self._raw_text))
        self._fix_height()

    def markdown(self):
        return self._raw_text

    def _format_code_block(self, match):
        """Форматирование блока кода с указанием языка"""
        lang = match.group(1) or "text"
        code = match.group(2)
        # Экранируем код, чтобы не сломать HTML
        code = html.escape(code)
    
        # Цвета для разных языков (просто иконка/название)
        lang_colors = {
            "python": "#3776AB",
            "javascript": "#F7DF1E",
            "html": "#E34F26",
            "css": "#1572B6",
            "json": "#000000",
            "yaml": "#CB171E",
            "xml": "#005F5F",
            "sql": "#4479A1",
            "bash": "#4EAA25",
            "powershell": "#5391FE",
            "c": "#00599C",
            "cpp": "#00599C",
            "csharp": "#239120",
            "java": "#007396",
            "go": "#00ADD8",
            "rust": "#000000",
            "php": "#777BB4",
            "ruby": "#CC342D",
            "swift": "#F05138",
            "kotlin": "#7F52FF",
            "typescript": "#3178C6",
        }
    
        lang_display = lang.upper() if lang != "text" else "TEXT"
        color = lang_colors.get(lang.lower(), "#666666")
    
        return f"""
        <div style="margin: 8px 0; border-radius: 8px; overflow: hidden; border: 1px solid #333;">
            <div style="background: #2d2d2d; padding: 4px 12px; border-bottom: 1px solid #444; display: flex; justify-content: space-between;">
                <span style="color: {color}; font-family: monospace; font-size: 12px; font-weight: 600;">{lang_display}</span>
                <span style="color: #888; font-family: monospace; font-size: 11px;">▼</span>
            </div>
            <pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; margin: 0; overflow-x: auto; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; line-height: 1.5;"><code>{code}</code></pre>
        </div>
        """