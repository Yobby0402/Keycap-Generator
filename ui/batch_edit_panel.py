"""
批量编辑参数面板
用于编辑同一类型按键的样式
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QDoubleSpinBox, QPushButton, QScrollArea,
                             QFormLayout, QLineEdit, QFileDialog, QComboBox,
                             QCheckBox, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Optional
from core.key_type_analyzer import KeyTypeSignature
from core.batch_edit_config import BatchEditConfig
from core.parameters import KeycapGeometry
from core.legend_mapping import LegendStyle, KLE_POSITION_NAMES
from core.keycap_presets import u_to_mm
from utils.file_utils import get_system_fonts, get_font_name


class BatchEditPanel(QWidget):
    """批量编辑参数面板"""
    
    # 信号：配置保存
    config_saved = pyqtSignal(BatchEditConfig)
    # 信号：配置改变（实时预览）
    config_changed = pyqtSignal(BatchEditConfig)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_type: Optional[KeyTypeSignature] = None
        self.current_config: Optional[BatchEditConfig] = None
        self.style_widgets: dict = {}  # {位置索引: 样式控件组}
        self.default_font_path: Optional[str] = None  # 默认字体路径
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 类型信息
        self.type_label = QLabel("未选择类型")
        self.type_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.type_label)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 几何参数（共用）
        self.geometry_group = QGroupBox("几何参数（所有该类型按键共用）")
        self.geometry_layout = QFormLayout()
        self.geometry_group.setLayout(self.geometry_layout)
        content_layout.addWidget(self.geometry_group)
        
        # 字符样式（按位置）
        self.style_group = QGroupBox("字符样式")
        self.style_layout = QVBoxLayout()
        self.style_group.setLayout(self.style_layout)
        content_layout.addWidget(self.style_group)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # 保存按钮
        self.save_btn = QPushButton("保存并应用到所有该类型按键")
        self.save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.save_btn.clicked.connect(self.save_and_apply)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)
    
    def load_type(self, key_type: KeyTypeSignature, config: BatchEditConfig):
        """加载类型配置"""
        self.current_type = key_type
        self.current_config = config
        
        # 更新类型标签
        self.type_label.setText(f"类型: {key_type.to_string()}")
        
        # 清除旧控件
        self._clear_layout(self.geometry_layout)
        self._clear_style_widgets()
        
        # 加载几何参数
        self._load_geometry(config.geometry)
        
        # 加载字符样式（只为有字符的位置创建控件）
        self._load_text_styles(key_type, config)
        
        # 启用保存按钮
        self.save_btn.setEnabled(True)
    
    def _load_geometry(self, geometry: KeycapGeometry):
        """加载几何参数控件"""
        # 深度
        depth_spin = QDoubleSpinBox()
        depth_spin.setRange(1.0, 20.0)
        depth_spin.setValue(geometry.key_depth)
        depth_spin.setDecimals(1)
        depth_spin.setSuffix(" mm")
        depth_spin.valueChanged.connect(lambda v: self._on_geometry_changed('key_depth', v))
        self.geometry_layout.addRow("深度:", depth_spin)
        
        # 侧面斜角
        side_angle_spin = QDoubleSpinBox()
        side_angle_spin.setRange(0.0, 30.0)
        side_angle_spin.setValue(geometry.side_angle)
        side_angle_spin.setDecimals(1)
        side_angle_spin.setSuffix("°")
        side_angle_spin.valueChanged.connect(lambda v: self._on_geometry_changed('side_angle', v))
        self.geometry_layout.addRow("侧面斜角:", side_angle_spin)
        
        # 边缘形状设置
        edge_mode_combo = QComboBox()
        edge_mode_combo.addItems(["圆角", "45度斜角"])
        current_mode = getattr(geometry, 'edge_profile_mode', "fillet")
        edge_mode_combo.setCurrentText("45度斜角" if current_mode == "chamfer" else "圆角")
        edge_mode_combo.currentTextChanged.connect(
            lambda text: self._on_geometry_changed('edge_profile_mode',
                                                   "chamfer" if text == "45度斜角" else "fillet"))
        self.geometry_layout.addRow("边缘类型:", edge_mode_combo)

        edge_radius_spin = QDoubleSpinBox()
        edge_radius_spin.setRange(0.0, 5.0)
        edge_radius_spin.setValue(getattr(geometry, 'edge_profile_radius', 0.0))
        edge_radius_spin.setDecimals(2)
        edge_radius_spin.setSuffix(" mm")
        edge_radius_spin.valueChanged.connect(lambda v: self._on_geometry_changed('edge_profile_radius', v))
        self.geometry_layout.addRow("边缘半径:", edge_radius_spin)

        edge_apply_layout = QHBoxLayout()
        edge_outer_check = QCheckBox("外侧边缘")
        edge_outer_check.setChecked(getattr(geometry, 'edge_profile_outer', True))
        edge_outer_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_outer', v == Qt.Checked))
        edge_inner_check = QCheckBox("内侧边缘")
        edge_inner_check.setChecked(getattr(geometry, 'edge_profile_inner', False))
        edge_inner_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_inner', v == Qt.Checked))
        edge_apply_layout.addWidget(edge_outer_check)
        edge_apply_layout.addWidget(edge_inner_check)
        self.geometry_layout.addRow("生效范围:", edge_apply_layout)

        edge_sides_layout = QGridLayout()
        edge_left_check = QCheckBox("左")
        edge_right_check = QCheckBox("右")
        edge_top_check = QCheckBox("上")
        edge_bottom_check = QCheckBox("下")
        edge_left_check.setChecked(getattr(geometry, 'edge_profile_left', True))
        edge_right_check.setChecked(getattr(geometry, 'edge_profile_right', True))
        edge_top_check.setChecked(getattr(geometry, 'edge_profile_top', True))
        edge_bottom_check.setChecked(getattr(geometry, 'edge_profile_bottom', True))
        edge_left_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_left', v == Qt.Checked))
        edge_right_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_right', v == Qt.Checked))
        edge_top_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_top', v == Qt.Checked))
        edge_bottom_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_bottom', v == Qt.Checked))
        edge_sides_layout.addWidget(edge_left_check, 0, 0)
        edge_sides_layout.addWidget(edge_right_check, 0, 1)
        edge_sides_layout.addWidget(edge_top_check, 1, 0)
        edge_sides_layout.addWidget(edge_bottom_check, 1, 1)
        self.geometry_layout.addRow("生效边:", edge_sides_layout)

        # 圆角半径
        corner_radius_spin = QDoubleSpinBox()
        corner_radius_spin.setRange(0.0, 5.0)
        corner_radius_spin.setValue(geometry.corner_radius)
        corner_radius_spin.setDecimals(2)
        corner_radius_spin.setSuffix(" mm")
        corner_radius_spin.valueChanged.connect(lambda v: self._on_geometry_changed('corner_radius', v))
        self.geometry_layout.addRow("圆角半径:", corner_radius_spin)
        
        # 卫星轴设置
        from PyQt5.QtWidgets import QCheckBox, QComboBox
        stabilizer_enabled_check = QCheckBox("启用卫星轴连接器")
        stabilizer_enabled_check.setChecked(getattr(geometry, 'stabilizer_enabled', False))
        stabilizer_enabled_check.stateChanged.connect(lambda v: self._on_geometry_changed('stabilizer_enabled', v == Qt.Checked))
        self.geometry_layout.addRow("", stabilizer_enabled_check)
        
        # 卫星轴类型选择（常用两种：2u和6.25u）
        stabilizer_type_combo = QComboBox()
        stabilizer_type_combo.addItem("自定义", -1)
        stabilizer_type_combo.addItem("2u (标准)", 2.0)
        stabilizer_type_combo.addItem("6.25u (空格键)", 6.25)
        stabilizer_type_combo.currentIndexChanged.connect(lambda idx: self._on_stabilizer_type_changed(stabilizer_type_combo, stabilizer_length_spin))
        self.geometry_layout.addRow("卫星轴类型:", stabilizer_type_combo)
        
        stabilizer_length_spin = QDoubleSpinBox()
        stabilizer_length_spin.setRange(10.0, 200.0)
        stabilizer_length_spin.setValue(getattr(geometry, 'stabilizer_length', 50.0))
        stabilizer_length_spin.setDecimals(1)
        stabilizer_length_spin.setSuffix(" mm")
        stabilizer_length_spin.valueChanged.connect(lambda v: self._on_geometry_changed('stabilizer_length', v))
        # 当长度改变时，如果与预设值不匹配，切换到"自定义"
        stabilizer_length_spin.valueChanged.connect(lambda v: self._update_stabilizer_type_combo(stabilizer_type_combo, v))
        self.geometry_layout.addRow("卫星轴长度:", stabilizer_length_spin)
        
        # 初始化类型选择
        current_length = getattr(geometry, 'stabilizer_length', 50.0)
        from core.keycap_presets import u_to_mm
        if abs(current_length - u_to_mm(2.0)) < 1.0:  # 允许1mm误差
            stabilizer_type_combo.setCurrentIndex(1)
        elif abs(current_length - u_to_mm(6.25)) < 1.0:
            stabilizer_type_combo.setCurrentIndex(2)
        else:
            stabilizer_type_combo.setCurrentIndex(0)
    
    def _load_text_styles(self, key_type: KeyTypeSignature, config: BatchEditConfig):
        """加载字符样式控件"""
        # 只为有字符的位置创建控件
        for pos_idx in sorted(key_type.label_positions):
            pos_name = KLE_POSITION_NAMES.get(pos_idx, f"位置{pos_idx}")
            style = config.get_style_for_position(pos_idx, self.default_font_path)
            
            # 创建位置组
            pos_group = QGroupBox(f"{pos_name} (位置{pos_idx})")
            pos_layout = QFormLayout()
            
            # 字体选择
            font_layout = QHBoxLayout()
            font_combo = QComboBox()
            font_combo.setEditable(False)
            self._load_fonts_to_combo(font_combo)
            # 设置当前字体
            current_font_path = style.font_path or self.default_font_path
            if current_font_path:
                self._set_font_in_combo(font_combo, current_font_path)
            font_combo.currentIndexChanged.connect(lambda idx, p=pos_idx, combo=font_combo: self._update_style_font(p, combo))
            
            browse_btn = QPushButton("浏览...")
            browse_btn.clicked.connect(lambda checked=False, p=pos_idx, combo=font_combo: self._browse_font_for_position(p, combo))
            
            font_layout.addWidget(font_combo)
            font_layout.addWidget(browse_btn)
            pos_layout.addRow("字体:", font_layout)
            
            # 字体大小
            size_spin = QDoubleSpinBox()
            size_spin.setRange(1.0, 20.0)
            size_spin.setValue(style.size)
            size_spin.setDecimals(1)
            size_spin.setSuffix(" mm")
            size_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_size(p, v))
            pos_layout.addRow("大小:", size_spin)
            
            # 深度
            depth_spin = QDoubleSpinBox()
            depth_spin.setRange(-2.0, 2.0)
            depth_spin.setValue(style.depth)
            depth_spin.setDecimals(2)
            depth_spin.setSuffix(" mm")
            depth_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_depth(p, v))
            pos_layout.addRow("深度:", depth_spin)
            
            # X偏移
            offset_x_spin = QDoubleSpinBox()
            offset_x_spin.setRange(-20.0, 20.0)
            offset_x_spin.setValue(style.offset_x)
            offset_x_spin.setDecimals(2)
            offset_x_spin.setSuffix(" mm")
            offset_x_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_offset_x(p, v))
            pos_layout.addRow("X偏移:", offset_x_spin)
            
            # Y偏移
            offset_y_spin = QDoubleSpinBox()
            offset_y_spin.setRange(-20.0, 20.0)
            offset_y_spin.setValue(style.offset_y)
            offset_y_spin.setDecimals(2)
            offset_y_spin.setSuffix(" mm")
            offset_y_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_offset_y(p, v))
            pos_layout.addRow("Y偏移:", offset_y_spin)
            
            pos_group.setLayout(pos_layout)
            self.style_layout.addWidget(pos_group)
            
            # 保存控件引用
            self.style_widgets[pos_idx] = {
                'font': font_combo,
                'size': size_spin,
                'depth': depth_spin,
                'offset_x': offset_x_spin,
                'offset_y': offset_y_spin
            }
    
    def _load_fonts_to_combo(self, combo: QComboBox):
        """加载字体到组合框"""
        try:
            fonts = get_system_fonts()
            for font_path in fonts:
                font_name = get_font_name(font_path)
                combo.addItem(font_name, font_path)
        except Exception as e:
            print(f"加载系统字体时出错: {e}")
    
    def _set_font_in_combo(self, combo: QComboBox, font_path: str):
        """在组合框中设置字体"""
        for i in range(combo.count()):
            if combo.itemData(i) == font_path:
                combo.setCurrentIndex(i)
                return
        # 如果没找到，添加它
        font_name = get_font_name(font_path)
        combo.addItem(font_name, font_path)
        combo.setCurrentIndex(combo.count() - 1)
    
    def _browse_font_for_position(self, pos_idx: int, combo: QComboBox):
        """为指定位置浏览字体文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择字体文件 (位置{pos_idx})",
            "",
            "字体文件 (*.ttf *.otf *.ttc);;所有文件 (*.*)"
        )
        
        if file_path:
            font_name = get_font_name(file_path)
            combo.addItem(font_name, file_path)
            combo.setCurrentIndex(combo.count() - 1)
            # 更新样式
            self._update_style_font(pos_idx, combo)
    
    def _on_stabilizer_type_changed(self, type_combo: QComboBox, length_spin: QDoubleSpinBox):
        """卫星轴类型改变"""
        type_value = type_combo.currentData()
        if type_value != -1:  # 不是"自定义"
            # 转换为mm单位
            length_mm = u_to_mm(type_value)
            # 临时断开信号，避免触发类型切换
            length_spin.blockSignals(True)
            length_spin.setValue(length_mm)
            length_spin.blockSignals(False)
            # 更新配置
            self._on_geometry_changed('stabilizer_length', length_mm)
    
    def _update_stabilizer_type_combo(self, type_combo: QComboBox, length_mm: float):
        """根据长度更新类型选择（如果与预设值不匹配，切换到自定义）"""
        if type_combo.currentData() == -1:  # 已经是自定义，不更新
            return
        # 检查是否与预设值匹配
        if abs(length_mm - u_to_mm(2.0)) < 1.0:
            if type_combo.currentIndex() != 1:
                type_combo.setCurrentIndex(1)
        elif abs(length_mm - u_to_mm(6.25)) < 1.0:
            if type_combo.currentIndex() != 2:
                type_combo.setCurrentIndex(2)
        else:
            if type_combo.currentIndex() != 0:
                type_combo.setCurrentIndex(0)
    
    def _update_style_font(self, pos_idx: int, combo: QComboBox):
        """更新样式字体"""
        if self.current_config:
            font_path = combo.itemData(combo.currentIndex())
            if pos_idx in self.current_config.text_styles:
                self.current_config.text_styles[pos_idx].font_path = font_path
            else:
                self.current_config.text_styles[pos_idx] = LegendStyle(font_path=font_path)
            # 实时更新预览
            self.config_changed.emit(self.current_config)
    
    def set_default_font(self, font_path: Optional[str]):
        """设置默认字体路径"""
        self.default_font_path = font_path
    
    def _on_geometry_changed(self, attr: str, value: float):
        """几何参数改变"""
        if self.current_config:
            setattr(self.current_config.geometry, attr, value)
            # 实时更新预览
            self.config_changed.emit(self.current_config)
    
    def _update_style_size(self, pos_idx: int, value: float):
        """更新样式大小"""
        if self.current_config:
            if pos_idx in self.current_config.text_styles:
                self.current_config.text_styles[pos_idx].size = value
            else:
                self.current_config.text_styles[pos_idx] = LegendStyle(size=value)
            # 实时更新预览
            self.config_changed.emit(self.current_config)
    
    def _update_style_depth(self, pos_idx: int, value: float):
        """更新样式深度"""
        if self.current_config:
            if pos_idx in self.current_config.text_styles:
                self.current_config.text_styles[pos_idx].depth = value
            else:
                self.current_config.text_styles[pos_idx] = LegendStyle(depth=value)
            # 实时更新预览
            self.config_changed.emit(self.current_config)
    
    def _update_style_offset_x(self, pos_idx: int, value: float):
        """更新样式X偏移"""
        if self.current_config:
            if pos_idx in self.current_config.text_styles:
                self.current_config.text_styles[pos_idx].offset_x = value
            else:
                self.current_config.text_styles[pos_idx] = LegendStyle(offset_x=value)
            # 实时更新预览
            self.config_changed.emit(self.current_config)
    
    def _update_style_offset_y(self, pos_idx: int, value: float):
        """更新样式Y偏移"""
        if self.current_config:
            if pos_idx in self.current_config.text_styles:
                self.current_config.text_styles[pos_idx].offset_y = value
            else:
                self.current_config.text_styles[pos_idx] = LegendStyle(offset_y=value)
            # 实时更新预览
            self.config_changed.emit(self.current_config)
    
    def _clear_layout(self, layout: QFormLayout):
        """清除布局中的所有项"""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _clear_style_widgets(self):
        """清除样式控件"""
        while self.style_layout.count():
            item = self.style_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.style_widgets.clear()
    
    def save_and_apply(self):
        """保存并应用到所有该类型按键"""
        if self.current_config is None:
            return
        
        # 发出信号
        self.config_saved.emit(self.current_config)
