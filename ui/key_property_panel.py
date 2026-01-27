"""
按键属性面板
显示选中按键的属性信息，并支持编辑
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox,
                             QFormLayout, QScrollArea, QPushButton, QLineEdit,
                             QDoubleSpinBox, QTableWidget, QTableWidgetItem,
                             QStackedWidget, QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from core.kle_parser import KLEKey
from core.legend_mapping import KLE_POSITION_NAMES
from core.batch_edit_config import BatchEditConfig
from typing import Optional

class KeyPropertyPanel(QWidget):
    """按键属性面板（支持编辑）"""
    
    # 信号：数据更新
    data_updated = pyqtSignal(int, KLEKey)  # (key_index, updated_key)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_key: KLEKey = None
        self.current_key_index: int = -1
        self.current_batch_config: Optional[BatchEditConfig] = None  # 当前按键对应的批量编辑配置
        self.setup_ui()
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题和切换按钮
        header_layout = QHBoxLayout()
        title_label = QLabel("按键属性")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 切换按钮
        self.switch_btn = QPushButton("切换到字符编辑")
        self.switch_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.switch_btn.clicked.connect(self.switch_view)
        header_layout.addWidget(self.switch_btn)
        layout.addLayout(header_layout)
        
        # 堆叠界面：属性视图和字符编辑视图
        self.stacked_widget = QStackedWidget()
        
        # ===== 视图1：按键属性 =====
        property_widget = QWidget()
        property_layout = QVBoxLayout(property_widget)
        property_layout.setContentsMargins(0, 0, 0, 0)
        
        property_scroll = QScrollArea()
        property_scroll.setWidgetResizable(True)
        property_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        property_content = QWidget()
        property_content_layout = QVBoxLayout(property_content)
        property_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 基本信息
        self.info_group = QGroupBox("基本信息")
        self.info_layout = QFormLayout()
        self.info_group.setLayout(self.info_layout)
        property_content_layout.addWidget(self.info_group)
        
        # 按键上已有字符（选中键时直接可见，无需切到字符编辑）
        self.chars_display_group = QGroupBox("按键字符")
        self.chars_display_layout = QFormLayout()
        self.chars_display_group.setLayout(self.chars_display_layout)
        property_content_layout.addWidget(self.chars_display_group)
        
        # 尺寸信息
        self.size_group = QGroupBox("尺寸")
        self.size_layout = QFormLayout()
        self.size_group.setLayout(self.size_layout)
        property_content_layout.addWidget(self.size_group)
        
        # 样式映射信息（显示批量编辑配置）
        self.style_group = QGroupBox("样式映射配置")
        self.style_layout = QFormLayout()
        self.style_group.setLayout(self.style_layout)
        property_content_layout.addWidget(self.style_group)
        
        # 颜色信息
        self.color_group = QGroupBox("颜色")
        self.color_layout = QFormLayout()
        self.color_group.setLayout(self.color_layout)
        property_content_layout.addWidget(self.color_group)
        
        property_content_layout.addStretch()
        property_scroll.setWidget(property_content)
        property_layout.addWidget(property_scroll)
        
        self.stacked_widget.addWidget(property_widget)
        
        # ===== 视图2：字符编辑 =====
        edit_widget = QWidget()
        edit_layout = QVBoxLayout(edit_widget)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        
        edit_scroll = QScrollArea()
        edit_scroll.setWidgetResizable(True)
        edit_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        edit_content = QWidget()
        edit_content_layout = QVBoxLayout(edit_content)
        edit_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 字符编辑说明
        edit_info = QLabel("编辑按键的字符内容（KLE 12位置）")
        edit_info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        edit_content_layout.addWidget(edit_info)
        
        # 字符编辑表格
        self.chars_table = QTableWidget()
        self.chars_table.setColumnCount(2)
        self.chars_table.setHorizontalHeaderLabels(["位置", "字符"])
        self.chars_table.horizontalHeader().setStretchLastSection(True)
        self.chars_table.setRowCount(12)
        
        # 填充位置名称（只读）
        for i in range(12):
            pos_name = KLE_POSITION_NAMES.get(i, f"位置{i}")
            pos_item = QTableWidgetItem(pos_name)
            pos_item.setFlags(Qt.ItemIsEnabled)  # 位置名称不可编辑
            self.chars_table.setItem(i, 0, pos_item)
            
            # 字符输入框（可编辑）
            char_item = QTableWidgetItem("")
            self.chars_table.setItem(i, 1, char_item)
        
        edit_content_layout.addWidget(self.chars_table)
        edit_content_layout.addStretch()
        edit_scroll.setWidget(edit_content)
        edit_layout.addWidget(edit_scroll)
        
        self.stacked_widget.addWidget(edit_widget)
        
        layout.addWidget(self.stacked_widget)
        
        # 保存按钮（只在字符编辑视图显示）
        self.save_btn = QPushButton("保存更改")
        self.save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setEnabled(False)
        self.save_btn.setVisible(False)  # 默认隐藏（在属性视图）
        layout.addWidget(self.save_btn)
        
        # 初始状态：显示提示
        self.show_empty_state()
    
    def switch_view(self):
        """切换视图"""
        current_index = self.stacked_widget.currentIndex()
        if current_index == 0:  # 当前是属性视图，切换到字符编辑
            self.stacked_widget.setCurrentIndex(1)
            self.switch_btn.setText("切换到按键属性")
            self.save_btn.setVisible(True)
        else:  # 当前是字符编辑，切换到属性视图
            self.stacked_widget.setCurrentIndex(0)
            self.switch_btn.setText("切换到字符编辑")
            self.save_btn.setVisible(False)
    
    def show_empty_state(self):
        """显示空状态"""
        self.info_group.setVisible(False)
        self.chars_display_group.setVisible(False)
        self.size_group.setVisible(False)
        self.style_group.setVisible(False)
        self.color_group.setVisible(False)
    
    def update_key(self, key: KLEKey, key_index: int = -1, batch_config: Optional[BatchEditConfig] = None):
        """更新显示的按键
        
        参数:
            key: KLE按键对象
            key_index: 按键索引
            batch_config: 对应的批量编辑配置（可选）
        """
        self.current_key = key
        self.current_key_index = key_index
        self.current_batch_config = batch_config
        
        print(f"【属性面板更新】按键索引: {key_index}")
        print(f"  - batch_config: {batch_config is not None}")
        if batch_config:
            print(f"  - 配置类型: {batch_config.key_type.to_string()}")
        else:
            print(f"  - 使用默认配置")
        
        if key is None:
            self.show_empty_state()
            self.save_btn.setEnabled(False)
            return
        
        # 显示所有组
        self.info_group.setVisible(True)
        self.size_group.setVisible(True)
        self.style_group.setVisible(True)
        self.color_group.setVisible(True)
        self.save_btn.setEnabled(True)
        
        # 清除旧内容（注意：必须在显示新内容之前清除）
        self._clear_layout(self.info_layout)
        self._clear_layout(self.chars_display_layout)
        self._clear_layout(self.size_layout)
        self._clear_layout(self.style_layout)
        self._clear_layout(self.color_layout)
        
        # 按键上已有字符（非空位置 → 位置名: 字符）
        parts = []
        for pos_idx, label in enumerate(key.labels or []):
            if label and str(label).strip():
                pos_name = KLE_POSITION_NAMES.get(pos_idx, f"位置{pos_idx}")
                parts.append(f"{pos_name}: {label.strip()}")
        if parts:
            chars_text = "\n".join(parts)
            chars_lbl = QLabel(chars_text)
            chars_lbl.setWordWrap(True)
            chars_lbl.setStyleSheet("color: #333; font-size: 12px; padding: 4px 0;")
            self.chars_display_layout.addRow(chars_lbl)
        else:
            none_lbl = QLabel("（无字符）")
            none_lbl.setStyleSheet("color: #999; font-style: italic;")
            self.chars_display_layout.addRow(none_lbl)
        self.chars_display_group.setVisible(True)
        
        # 基本信息
        self._add_form_item(self.info_layout, "位置", f"({key.x:.2f}, {key.y:.2f}) u")
        if key.row is not None:
            self._add_form_item(self.info_layout, "行号", f"{key.row}")
        if key.rotation_angle != 0:
            self._add_form_item(self.info_layout, "旋转角度", f"{key.rotation_angle}°")
        if key.rotation_x != 0 or key.rotation_y != 0:
            self._add_form_item(self.info_layout, "旋转中心", f"({key.rotation_x:.2f}, {key.rotation_y:.2f})")
        
        # 尺寸信息
        self._add_form_item(self.size_layout, "宽度", f"{key.width:.2f} u")
        self._add_form_item(self.size_layout, "高度", f"{key.height:.2f} u")
        
        # 字符信息（填充到表格）
        for i, label in enumerate(key.labels):
            if i < 12:
                char_item = self.chars_table.item(i, 1)
                if char_item:
                    char_item.setText(label if label else "")
        
        # 样式映射信息（显示批量编辑配置）- 整理显示
        if self.current_batch_config:
            config = self.current_batch_config
            print(f"  - 显示配置信息: {config.key_type.to_string()}")
            
            # 类型标识
            self._add_form_item(self.style_layout, "类型标识", config.key_type.to_string())
            
            # 几何参数
            geometry_label = QLabel("几何参数")
            geometry_label.setStyleSheet("font-weight: bold; color: #333; margin-top: 5px;")
            self.style_layout.addRow("", geometry_label)
            
            self._add_form_item(self.style_layout, "深度", f"{config.geometry.key_depth:.1f} mm")
            self._add_form_item(self.style_layout, "侧面斜角", f"{config.geometry.side_angle:.1f}°")
            self._add_form_item(self.style_layout, "圆角半径", f"{config.geometry.corner_radius:.2f} mm")
            edge_mode = getattr(config.geometry, 'edge_profile_mode', "fillet")
            edge_mode_text = "45度斜角" if edge_mode == "chamfer" else "圆角"
            edge_radius = getattr(config.geometry, 'edge_profile_radius', 0.0)
            edge_outer = getattr(config.geometry, 'edge_profile_outer', True)
            edge_inner = getattr(config.geometry, 'edge_profile_inner', False)
            edge_sides = []
            if getattr(config.geometry, 'edge_profile_left', True):
                edge_sides.append("左")
            if getattr(config.geometry, 'edge_profile_right', True):
                edge_sides.append("右")
            if getattr(config.geometry, 'edge_profile_top', True):
                edge_sides.append("上")
            if getattr(config.geometry, 'edge_profile_bottom', True):
                edge_sides.append("下")
            edge_range = []
            if edge_outer:
                edge_range.append("外侧")
            if edge_inner:
                edge_range.append("内侧")
            self._add_form_item(self.style_layout, "边缘类型", edge_mode_text)
            self._add_form_item(self.style_layout, "边缘半径", f"{edge_radius:.2f} mm")
            self._add_form_item(self.style_layout, "生效范围", " / ".join(edge_range) if edge_range else "无")
            self._add_form_item(self.style_layout, "生效边", " / ".join(edge_sides) if edge_sides else "无")
            
            # 卫星轴信息
            stabilizer_enabled = getattr(config.geometry, 'stabilizer_enabled', False)
            stabilizer_length = getattr(config.geometry, 'stabilizer_length', 50.0)
            stabilizer_status = "启用" if stabilizer_enabled else "禁用"
            stabilizer_color = "#28a745" if stabilizer_enabled else "#6c757d"
            stabilizer_text = f'<span style="color: {stabilizer_color};">{stabilizer_status}</span> ({stabilizer_length:.1f}mm)'
            stabilizer_label = QLabel(stabilizer_text)
            stabilizer_label.setTextFormat(Qt.RichText)
            self.style_layout.addRow("卫星轴:", stabilizer_label)
            
            # 字符样式信息
            if config.text_styles:
                style_label_header = QLabel("字符样式")
                style_label_header.setStyleSheet("font-weight: bold; color: #333; margin-top: 5px;")
                self.style_layout.addRow("", style_label_header)
                
                style_info = []
                for pos_idx, style in sorted(config.text_styles.items()):
                    pos_name = KLE_POSITION_NAMES.get(pos_idx, f"位置{pos_idx}")
                    font_name = "默认字体"
                    if style.font_path:
                        from utils.file_utils import get_font_name
                        font_name = get_font_name(style.font_path) or "未知字体"
                    style_info.append(f"  • {pos_name}: {font_name}, {style.size:.1f}mm, 深度{style.depth:.1f}mm")
                if style_info:
                    style_text = "\n".join(style_info)
                    style_label = QLabel(style_text)
                    style_label.setWordWrap(True)
                    style_label.setStyleSheet("color: #666; font-size: 10px; padding-left: 10px;")
                    self.style_layout.addRow("", style_label)
        else:
            print(f"  - 未找到配置，显示默认配置提示")
            default_label = QLabel("使用默认配置\n（请在批量编辑界面配置）")
            default_label.setStyleSheet("color: #999; font-style: italic; padding: 10px;")
            self.style_layout.addRow("", default_label)
        
        # 颜色信息
        if key.key_color:
            color_label = QLabel()
            color_label.setStyleSheet(f"background-color: {key.key_color}; border: 1px solid #ccc; min-width: 50px; min-height: 20px;")
            self._add_form_item(self.color_layout, "按键颜色", "")
            self.color_layout.addRow("", color_label)
        
        if key.text_color:
            text_color_label = QLabel()
            text_color_label.setStyleSheet(f"background-color: {key.text_color}; border: 1px solid #ccc; min-width: 50px; min-height: 20px;")
            self._add_form_item(self.color_layout, "文字颜色", "")
            self.color_layout.addRow("", text_color_label)
        
        if not key.key_color and not key.text_color:
            no_color = QLabel("默认颜色")
            no_color.setStyleSheet("color: gray;")
            self.color_layout.addRow("", no_color)
    
    def save_changes(self):
        """保存更改"""
        if self.current_key is None or self.current_key_index < 0:
            return
        
        # 更新 key 的 labels
        new_labels = []
        for i in range(12):
            char_item = self.chars_table.item(i, 1)
            char_text = char_item.text() if char_item else ""
            new_labels.append(char_text)
        
        # 更新 key 对象
        self.current_key.labels = new_labels
        
        # 发出信号
        self.data_updated.emit(self.current_key_index, self.current_key)
    
    def _clear_layout(self, layout):
        """清除布局中的所有项"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _add_form_item(self, layout: QFormLayout, label: str, value: str):
        """添加表单项"""
        value_label = QLabel(value)
        layout.addRow(label + ":", value_label)
