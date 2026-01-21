"""
设置对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QComboBox, QGridLayout)
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
        
        # 默认参数设置组
        default_params_group = QGroupBox("默认按键参数")
        default_params_layout = QVBoxLayout()
        
        # 默认侧面斜角
        side_angle_layout = QHBoxLayout()
        side_angle_layout.addWidget(QLabel("默认侧面斜角:"))
        self.default_side_angle_spin = QDoubleSpinBox()
        self.default_side_angle_spin.setRange(0.0, 30.0)
        self.default_side_angle_spin.setDecimals(1)
        self.default_side_angle_spin.setSuffix(" °")
        side_angle_layout.addWidget(self.default_side_angle_spin)
        default_params_layout.addLayout(side_angle_layout)
        
        # 默认边缘形状
        edge_mode_layout = QHBoxLayout()
        edge_mode_layout.addWidget(QLabel("默认边缘类型:"))
        self.default_edge_mode_combo = QComboBox()
        self.default_edge_mode_combo.addItems(["圆角", "45度斜角"])
        edge_mode_layout.addWidget(self.default_edge_mode_combo)
        default_params_layout.addLayout(edge_mode_layout)

        edge_radius_layout = QHBoxLayout()
        edge_radius_layout.addWidget(QLabel("默认边缘半径:"))
        self.default_edge_radius_spin = QDoubleSpinBox()
        self.default_edge_radius_spin.setRange(0.0, 5.0)
        self.default_edge_radius_spin.setDecimals(2)
        self.default_edge_radius_spin.setSuffix(" mm")
        edge_radius_layout.addWidget(self.default_edge_radius_spin)
        default_params_layout.addLayout(edge_radius_layout)

        edge_apply_layout = QHBoxLayout()
        self.default_edge_outer_check = QCheckBox("外侧边缘生效")
        self.default_edge_inner_check = QCheckBox("内侧边缘生效")
        edge_apply_layout.addWidget(self.default_edge_outer_check)
        edge_apply_layout.addWidget(self.default_edge_inner_check)
        default_params_layout.addLayout(edge_apply_layout)

        edge_sides_layout = QGridLayout()
        self.default_edge_left_check = QCheckBox("左")
        self.default_edge_right_check = QCheckBox("右")
        self.default_edge_top_check = QCheckBox("上")
        self.default_edge_bottom_check = QCheckBox("下")
        edge_sides_layout.addWidget(QLabel("生效边:"), 0, 0)
        edge_sides_layout.addWidget(self.default_edge_left_check, 0, 1)
        edge_sides_layout.addWidget(self.default_edge_right_check, 0, 2)
        edge_sides_layout.addWidget(self.default_edge_top_check, 1, 1)
        edge_sides_layout.addWidget(self.default_edge_bottom_check, 1, 2)
        default_params_layout.addLayout(edge_sides_layout)
        
        default_params_group.setLayout(default_params_layout)
        layout.addWidget(default_params_group)
        
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
        
        # 加载默认参数
        self.default_side_angle_spin.setValue(self.settings.get_default_side_angle())

        # 边缘形状默认参数
        mode_map = {"fillet": "圆角", "chamfer": "45度斜角"}
        default_mode = self.settings.get_default_edge_profile_mode()
        self.default_edge_mode_combo.setCurrentText(mode_map.get(default_mode, "圆角"))
        self.default_edge_radius_spin.setValue(self.settings.get_default_edge_profile_radius())
        self.default_edge_outer_check.setChecked(self.settings.get_default_edge_profile_outer())
        self.default_edge_inner_check.setChecked(self.settings.get_default_edge_profile_inner())
        self.default_edge_left_check.setChecked(self.settings.get_default_edge_profile_left())
        self.default_edge_right_check.setChecked(self.settings.get_default_edge_profile_right())
        self.default_edge_top_check.setChecked(self.settings.get_default_edge_profile_top())
        self.default_edge_bottom_check.setChecked(self.settings.get_default_edge_profile_bottom())
    
    def save_settings(self):
        """保存设置"""
        self.settings.set_snap_enabled(self.snap_checkbox.isChecked())
        self.settings.set_snap_grid_size(self.grid_spin.value())
        self.settings.set_auto_update(self.auto_update_checkbox.isChecked())
        
        # 保存默认参数
        self.settings.set_default_side_angle(self.default_side_angle_spin.value())

        # 边缘形状默认参数
        mode_map = {"圆角": "fillet", "45度斜角": "chamfer"}
        self.settings.set_default_edge_profile_mode(mode_map.get(self.default_edge_mode_combo.currentText(), "fillet"))
        self.settings.set_default_edge_profile_radius(self.default_edge_radius_spin.value())
        self.settings.set_default_edge_profile_outer(self.default_edge_outer_check.isChecked())
        self.settings.set_default_edge_profile_inner(self.default_edge_inner_check.isChecked())
        self.settings.set_default_edge_profile_left(self.default_edge_left_check.isChecked())
        self.settings.set_default_edge_profile_right(self.default_edge_right_check.isChecked())
        self.settings.set_default_edge_profile_top(self.default_edge_top_check.isChecked())
        self.settings.set_default_edge_profile_bottom(self.default_edge_bottom_check.isChecked())
    
    def accept(self):
        """确定按钮"""
        self.save_settings()
        super().accept()
