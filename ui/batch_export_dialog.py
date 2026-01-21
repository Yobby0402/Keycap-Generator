"""
批量导出对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QRadioButton, QButtonGroup,
                             QFileDialog, QMessageBox, QProgressBar, QGroupBox)
from PyQt5.QtCore import Qt
from typing import List
from core.kle_parser import KLEKey

class BatchExportDialog(QDialog):
    """批量导出对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量导出")
        self.setMinimumSize(400, 200)
        self.export_mode = "separate"  # "separate" 或 "merged"
        self.export_path = ""
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 导出模式选择
        mode_group = QGroupBox("导出模式")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup(self)
        
        self.separate_radio = QRadioButton("分离导出（每个按键独立文件）")
        self.separate_radio.setChecked(True)
        self.mode_group.addButton(self.separate_radio, 0)
        mode_layout.addWidget(self.separate_radio)
        
        self.merged_radio = QRadioButton("合并导出（所有按键摆盘在一个文件）")
        self.mode_group.addButton(self.merged_radio, 1)
        mode_layout.addWidget(self.merged_radio)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        ok_btn = QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def get_export_mode(self) -> str:
        """获取导出模式"""
        if self.merged_radio.isChecked():
            return "merged"
        return "separate"
