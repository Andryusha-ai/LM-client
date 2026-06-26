from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QHBoxLayout,QScrollArea

from .attachment_card import AttachmentCard

class AttachmentBar(QScrollArea):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QScrollArea.NoFrame)

        self._container=QWidget()
        self._layout=QHBoxLayout(self._container)
        self._layout.setContentsMargins(0,0,0,0)
        self._layout.setSpacing(8)
        self._layout.addStretch()

        self.setWidget(self._container)
        self._cards=[]

    def addAttachment(self,path:str):
        card=AttachmentCard(path)
        card.removed.connect(self.removeAttachment)
        self._layout.insertWidget(self._layout.count()-1,card)
        self._cards.append(card)
        self.setVisible(True)

    def removeAttachment(self,path:str):
        for card in self._cards[:]:
            if card.file_path==path:
                self._layout.removeWidget(card)
                card.deleteLater()
                self._cards.remove(card)
        if not self._cards:
            self.setVisible(False)

    def clear(self):
        for c in self._cards[:]:
            self._layout.removeWidget(c)
            c.deleteLater()
        self._cards.clear()
        self.setVisible(False)

    def attachments(self):
        return [c.file_path for c in self._cards]
