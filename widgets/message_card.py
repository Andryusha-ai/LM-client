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
        self.text.setHtml(self._to_html(text))

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

    def _to_html(self, text: str) -> str:
        """Конвертируем plain text в HTML с word-break"""
        escaped = html.escape(text).replace('\n', '<br>')
        return f"""
        <html><body>
        <p style="
            font-size: 14px;
            color: #111111;
            word-break: break-all;
            white-space: pre-wrap;
            margin: 0; padding: 0;
        ">{escaped}</p>
        </body></html>
        """

    # --------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        max_w = int(self.width() * 0.75)
        self.bubble.setMaximumWidth(max_w)
        # Пересчитываем высоту текста под новую ширину
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
        """)

    # --------------------------------------------------

    def setText(self, text: str):
        self._raw_text = text
        self.text.setHtml(self._to_html(text))
        self._fix_height()

    def appendText(self, text: str):
        self._raw_text += text
        self.text.setHtml(self._to_html(self._raw_text))
        self._fix_height()

    def markdown(self):
        return self._raw_text
