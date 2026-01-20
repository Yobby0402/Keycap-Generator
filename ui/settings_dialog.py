"""
设置对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox)
from PyQt5.QtCore import Qt
from core.settings import Settings


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("设置")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 对齐设置组
        snap_group = QGroupBox("对齐设置")
        snap_layout = QVBoxLayout()
        
        # 启用对齐
        self.snap_checkbox = QCheckBox("启用对齐吸附")
        self.snap_checkbox.setChecked(self.settings.get_snap_enabled())
        snap_layout.addWidget(self.snap_checkbox)
        
        # 网格大小
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("网格大小:"))
        self.grid_spin = QDoubleSpinBox()
        self.grid_spin.setRange(0.1, 10.0)
        self.grid_spin.setValue(self.settings.get_snap_grid_size())
        self.grid_spin.setDecimals(1)
        self.grid_spin.setSuffix(" mm")
        grid_layout.addWidget(self.grid_spin)
        snap_layout.addLayout(grid_layout)
        
        snap_group.setLayout(snap_layout)
        layout.addWidget(snap_group)
        
        # 性能设置组
        perf_group = QGroupBox("性能设置")
        perf_layout = QVBoxLayout()
        
        self.auto_update_checkbox = QCheckBox("开启实时刷新 (修改参数或拖动时自动重新计算模型)")
        self.auto_update_checkbox.setToolTip("开启后，修改参数或拖动文字结束后会自动重新生成模型。\n警告：复杂模型可能会导致卡顿。")
        perf_layout.addWidget(self.auto_update_checkbox)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """加载设置"""
        self.snap_checkbox.setChecked(self.settings.get_snap_enabled())
        self.grid_spin.setValue(self.settings.get_snap_grid_size())
        self.auto_update_checkbox.setChecked(self.settings.get_auto_update())
    
    def save_settings(self):
        """保存设置"""
        self.settings.set_snap_enabled(self.snap_checkbox.isChecked())
        self.settings.set_snap_grid_size(self.grid_spin.value())
        self.settings.set_auto_update(self.auto_update_checkbox.isChecked())
    
    def accept(self):
        """确定按钮"""
        self.save_settings()
        super().accept()
