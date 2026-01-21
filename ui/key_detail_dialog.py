"""
按键详情编辑对话框
用于编辑 KLE 布局中单个按键的字符
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QGroupBox, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QDoubleSpinBox, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List, Optional
from core.kle_parser import KLEKey
from core.legend_mapping import KLE_POSITION_NAMES

class KeyDetailDialog(QDialog):
    """按键详情编辑对话框"""
    
    # 信号：数据更新
    data_updated = pyqtSignal(int, KLEKey)  # (key_index, updated_key)
    
    def __init__(self, key: KLEKey, key_index: int, parent=None):
        super().__init__(parent)
        self.key = key
        self.key_index = key_index
        self.setWindowTitle(f"编辑按键 #{key_index + 1}")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 按键信息
        info_group = QGroupBox("按键信息")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"位置: ({self.key.x:.2f}, {self.key.y:.2f}) u"))
        info_layout.addWidget(QLabel(f"尺寸: {self.key.width:.2f} × {self.key.height:.2f} u"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 字符编辑表格
        chars_group = QGroupBox("字符设置 (KLE 12位置)")
        chars_layout = QVBoxLayout()
        
        self.chars_table = QTableWidget()
        self.chars_table.setColumnCount(3)
        self.chars_table.setHorizontalHeaderLabels(["位置", "字符", "大小 (mm)"])
        self.chars_table.horizontalHeader().setStretchLastSection(True)
        self.chars_table.setRowCount(12)
        
        # 填充位置名称
        for i in range(12):
            pos_name = KLE_POSITION_NAMES.get(i, f"位置{i}")
            self.chars_table.setItem(i, 0, QTableWidgetItem(pos_name))
            self.chars_table.item(i, 0).setFlags(Qt.ItemIsEnabled)  # 位置名称不可编辑
            
            # 字符输入框
            char_item = QTableWidgetItem("")
            self.chars_table.setItem(i, 1, char_item)
            
            # 大小输入框（使用自定义控件）
            size_spin = QDoubleSpinBox()
            size_spin.setRange(1.0, 20.0)
            size_spin.setValue(3.0)
            size_spin.setDecimals(1)
            size_spin.setSuffix(" mm")
            self.chars_table.setCellWidget(i, 2, size_spin)
        
        chars_layout.addWidget(self.chars_table)
        chars_group.setLayout(chars_layout)
        layout.addWidget(chars_group, stretch=1)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        ok_btn = QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_and_save)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_data(self):
        """加载当前按键的数据"""
        # 填充字符
        for i, label in enumerate(self.key.labels):
            if i < 12:
                char_item = self.chars_table.item(i, 1)
                if char_item:
                    char_item.setText(label if label else "")
                
                # 更新大小（如果有 font_sizes 数据）
                if i < len(self.key.font_sizes):
                    size_widget = self.chars_table.cellWidget(i, 2)
                    if size_widget:
                        size_widget.setValue(self.key.font_sizes[i])
    
    def accept_and_save(self):
        """保存并关闭"""
        # 更新 key 的 labels
        new_labels = []
        for i in range(12):
            char_item = self.chars_table.item(i, 1)
            char_text = char_item.text() if char_item else ""
            new_labels.append(char_text)
        
        # 更新 key 对象
        self.key.labels = new_labels
        
        # 发出信号
        self.data_updated.emit(self.key_index, self.key)
        
        self.accept()
