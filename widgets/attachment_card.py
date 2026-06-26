from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame,QLabel,QPushButton,QHBoxLayout,QSizePolicy
from pathlib import Path

class AttachmentCard(QFrame):
    removed=Signal(str)
    def __init__(self,file_path,parent=None):
        super().__init__(parent);self.file_path=file_path;self.setFrameShape(QFrame.StyledPanel);l=QHBoxLayout(self);l.setContentsMargins(8,6,8,6);p=QLabel();p.setFixedSize(48,48);s=Path(file_path).suffix.lower();
        
        
        
        pix=QPixmap(file_path) if s in {'.png','.jpg','.jpeg','.bmp','.gif','.webp'} else QPixmap();
        p.setPixmap(pix.scaled(48,48,Qt.KeepAspectRatio,Qt.SmoothTransformation)) if not pix.isNull() else p.setText('🖼' if s in {'.png','.jpg','.jpeg','.bmp','.gif','.webp'} else '📄');n=QLabel(Path(file_path).name);n.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred);b=QPushButton('✕');b.setFixedWidth(28);b.clicked.connect(lambda:self.removed.emit(self.file_path));l.addWidget(p);l.addWidget(n);l.addWidget(b)
