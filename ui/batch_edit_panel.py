"""
批量编辑参数面板
用于编辑同一类型按键的样式
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QDoubleSpinBox, QPushButton, QScrollArea,
                             QFormLayout, QLineEdit, QFileDialog, QComboBox,
                             QCheckBox, QGridLayout, QColorDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from typing import Optional
from core.key_type_analyzer import KeyTypeSignature
from core.batch_edit_config import BatchEditConfig
from core.parameters import KeycapGeometry
from core.legend_mapping import LegendStyle, KLE_POSITION_NAMES
from core.keycap_presets import u_to_mm
from core.i18n import t
from utils.file_utils import get_system_fonts, get_font_name


class BatchEditPanel(QWidget):
    """批量编辑参数面板"""
    
    # 信号：配置保存
    config_saved = pyqtSignal(BatchEditConfig)
    # 信号：配置改变（实时预览）
    config_changed = pyqtSignal(BatchEditConfig)
    
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings  # 用于调节增量等，对键盘参数对应项生效
        self.current_type: Optional[KeyTypeSignature] = None
        self.current_config: Optional[BatchEditConfig] = None
        self.style_widgets: dict = {}  # {位置索引: 样式控件组}
        self.default_font_path: Optional[str] = None  # 默认字体路径
        self.setup_ui()
        self.retranslateUi()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 类型信息
        self.type_label = QLabel("")
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
        self.geometry_group = QGroupBox("")
        self.geometry_layout = QFormLayout()
        self.geometry_group.setLayout(self.geometry_layout)
        content_layout.addWidget(self.geometry_group)
        
        # 弧面设置（与单键参数面板一致）
        self.curved_group = QGroupBox("")
        self.curved_layout = QFormLayout()
        self.curved_group.setLayout(self.curved_layout)
        content_layout.addWidget(self.curved_group)
        
        # 字符样式（按位置）
        self.style_group = QGroupBox("")
        self.style_layout = QVBoxLayout()
        self.style_group.setLayout(self.style_layout)
        content_layout.addWidget(self.style_group)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # 保存按钮（可由外部隐藏，例如在键盘参数页把按钮放在右侧列）
        self.save_btn = QPushButton("")
        self.save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.save_btn.clicked.connect(self.save_and_apply)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)
    
    def set_show_save_button(self, visible: bool):
        """是否显示内置的保存按钮（键盘参数页可将按钮放到右侧列时隐藏）"""
        self.save_btn.setVisible(visible)
    
    def load_type(self, key_type: KeyTypeSignature, config: BatchEditConfig):
        """加载类型配置"""
        self.current_type = key_type
        self.current_config = config
        
        # 更新类型标签
        self.type_label.setText(f"{t('类型:', 'Type:')} {key_type.to_string()}")
        
        # 清除旧控件
        self._clear_layout(self.geometry_layout)
        self._clear_layout(self.curved_layout)
        self._clear_style_widgets()
        
        # 加载几何参数（含弧面、颜色）
        self._load_geometry(config.geometry, config)
        
        # 加载字符样式（只为有字符的位置创建控件）
        self._load_text_styles(key_type, config)
        
        # 启用保存按钮
        self.save_btn.setEnabled(True)
    
    def _load_geometry(self, geometry: KeycapGeometry, config: Optional[BatchEditConfig] = None):
        """加载几何参数控件（调节增量来自设置）；config 非空时追加按键/文字颜色（应用时写回该类型按键）"""
        s = self.settings
        # 深度
        depth_spin = QDoubleSpinBox()
        depth_spin.setRange(1.0, 20.0)
        depth_spin.setValue(geometry.key_depth)
        depth_spin.setDecimals(1)
        depth_spin.setSuffix(" mm")
        depth_spin.valueChanged.connect(lambda v: self._on_geometry_changed('key_depth', v))
        self.geometry_layout.addRow(t("深度:", "Depth:"), depth_spin)
        
        # 壁厚
        wall_spin = QDoubleSpinBox()
        wall_spin.setRange(0.5, 5.0)
        wall_spin.setValue(getattr(geometry, 'wall_thickness', 1.0))
        wall_spin.setDecimals(2)
        wall_spin.setSuffix(" mm")
        if s:
            wall_spin.setSingleStep(s.get_wall_thickness_step())
        wall_spin.valueChanged.connect(lambda v: self._on_geometry_changed('wall_thickness', v))
        self.geometry_layout.addRow(t("壁厚:", "Wall thickness:"), wall_spin)
        
        # 侧面斜角
        side_angle_spin = QDoubleSpinBox()
        side_angle_spin.setRange(0.0, 30.0)
        side_angle_spin.setValue(geometry.side_angle)
        side_angle_spin.setDecimals(1)
        side_angle_spin.setSuffix("°")
        if s:
            side_angle_spin.setSingleStep(s.get_side_angle_step())
        side_angle_spin.valueChanged.connect(lambda v: self._on_geometry_changed('side_angle', v))
        self.geometry_layout.addRow(t("侧面斜角:", "Side angle:"), side_angle_spin)
        
        # 边缘形状设置
        edge_mode_combo = QComboBox()
        edge_mode_combo.addItems([t("圆角", "Fillet"), t("45度斜角", "45° Chamfer")])
        current_mode = getattr(geometry, 'edge_profile_mode', "fillet")
        edge_mode_combo.setCurrentText(t("45度斜角", "45° Chamfer") if current_mode == "chamfer" else t("圆角", "Fillet"))
        edge_mode_combo.currentTextChanged.connect(
            lambda text: self._on_geometry_changed('edge_profile_mode',
                                                   "chamfer" if text == t("45度斜角", "45° Chamfer") else "fillet"))
        self.geometry_layout.addRow(t("边缘类型:", "Edge type:"), edge_mode_combo)

        edge_radius_spin = QDoubleSpinBox()
        edge_radius_spin.setRange(0.0, 5.0)
        edge_radius_spin.setValue(getattr(geometry, 'edge_profile_radius', 0.0))
        edge_radius_spin.setDecimals(2)
        edge_radius_spin.setSuffix(" mm")
        if s:
            edge_radius_spin.setSingleStep(s.get_edge_radius_step())
        edge_radius_spin.valueChanged.connect(lambda v: self._on_geometry_changed('edge_profile_radius', v))
        self.geometry_layout.addRow(t("边缘半径:", "Edge radius:"), edge_radius_spin)

        edge_apply_layout = QHBoxLayout()
        edge_outer_check = QCheckBox(t("外侧边缘", "Outer edge"))
        edge_outer_check.setChecked(getattr(geometry, 'edge_profile_outer', True))
        edge_outer_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_outer', v == Qt.Checked))
        edge_inner_check = QCheckBox(t("内侧边缘", "Inner edge"))
        edge_inner_check.setChecked(getattr(geometry, 'edge_profile_inner', False))
        edge_inner_check.stateChanged.connect(lambda v: self._on_geometry_changed('edge_profile_inner', v == Qt.Checked))
        edge_apply_layout.addWidget(edge_outer_check)
        edge_apply_layout.addWidget(edge_inner_check)
        self.geometry_layout.addRow(t("生效范围:", "Apply to:"), edge_apply_layout)

        edge_sides_layout = QGridLayout()
        edge_left_check = QCheckBox(t("左", "Left"))
        edge_right_check = QCheckBox(t("右", "Right"))
        edge_top_check = QCheckBox(t("上", "Top"))
        edge_bottom_check = QCheckBox(t("下", "Bottom"))
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
        self.geometry_layout.addRow(t("生效边:", "Active sides:"), edge_sides_layout)

        # 圆角半径
        corner_radius_spin = QDoubleSpinBox()
        corner_radius_spin.setRange(0.0, 5.0)
        corner_radius_spin.setValue(geometry.corner_radius)
        corner_radius_spin.setDecimals(2)
        corner_radius_spin.setSuffix(" mm")
        corner_radius_spin.valueChanged.connect(lambda v: self._on_geometry_changed('corner_radius', v))
        self.geometry_layout.addRow(t("圆角半径:", "Corner radius:"), corner_radius_spin)
        
        # 卫星轴设置（QCheckBox/QComboBox 已在文件顶部导入）
        stabilizer_enabled_check = QCheckBox(t("启用卫星轴连接器", "Enable stabilizer"))
        stabilizer_enabled_check.setChecked(getattr(geometry, 'stabilizer_enabled', False))
        stabilizer_enabled_check.stateChanged.connect(lambda v: self._on_geometry_changed('stabilizer_enabled', v == Qt.Checked))
        self.geometry_layout.addRow("", stabilizer_enabled_check)
        
        # 卫星轴类型选择（常用两种：2u和6.25u）
        stabilizer_type_combo = QComboBox()
        stabilizer_type_combo.addItem(t("自定义", "Custom"), -1)
        stabilizer_type_combo.addItem(t("2u (标准)", "2u (Standard)"), 2.0)
        stabilizer_type_combo.addItem(t("6.25u (空格键)", "6.25u (Spacebar)"), 6.25)
        stabilizer_type_combo.currentIndexChanged.connect(lambda idx: self._on_stabilizer_type_changed(stabilizer_type_combo, stabilizer_length_spin))
        self.geometry_layout.addRow(t("卫星轴类型:", "Stabilizer type:"), stabilizer_type_combo)
        
        stabilizer_length_spin = QDoubleSpinBox()
        stabilizer_length_spin.setRange(10.0, 200.0)
        stabilizer_length_spin.setValue(getattr(geometry, 'stabilizer_length', 50.0))
        stabilizer_length_spin.setDecimals(1)
        stabilizer_length_spin.setSuffix(" mm")
        stabilizer_length_spin.valueChanged.connect(lambda v: self._on_geometry_changed('stabilizer_length', v))
        # 当长度改变时，如果与预设值不匹配，切换到"自定义"
        stabilizer_length_spin.valueChanged.connect(lambda v: self._update_stabilizer_type_combo(stabilizer_type_combo, v))
        self.geometry_layout.addRow(t("卫星轴长度:", "Stabilizer length:"), stabilizer_length_spin)
        
        # 初始化类型选择
        current_length = getattr(geometry, 'stabilizer_length', 50.0)
        from core.keycap_presets import u_to_mm
        if abs(current_length - u_to_mm(2.0)) < 1.0:  # 允许1mm误差
            stabilizer_type_combo.setCurrentIndex(1)
        elif abs(current_length - u_to_mm(6.25)) < 1.0:
            stabilizer_type_combo.setCurrentIndex(2)
        else:
            stabilizer_type_combo.setCurrentIndex(0)
        
        # 按键/文字颜色（应用时写回该类型按键，更新一次不锁定）
        if config is not None:
            key_color = getattr(config, 'key_color', None) or "#cccccc"
            text_color = getattr(config, 'text_color', None) or "#000000"
            def _pick_color(attr: str, default_hex: str, btn: QPushButton):
                q = QColor(default_hex)
                color = QColorDialog.getColor(q, self, "选择颜色")
                if color.isValid():
                    hex_val = color.name()
                    setattr(config, attr, hex_val)
                    btn.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #666; min-width: 50px; min-height: 22px;")
                    self.config_changed.emit(self.current_config)
            key_color_btn = QPushButton()
            key_color_btn.setStyleSheet(f"background-color: {key_color}; border: 1px solid #666; min-width: 50px; min-height: 22px;")
            key_color_btn.setCursor(Qt.PointingHandCursor)
            key_color_btn.clicked.connect(lambda: _pick_color('key_color', key_color, key_color_btn))
            self.geometry_layout.addRow(t("按键颜色:", "Key color:"), key_color_btn)
            text_color_btn = QPushButton()
            text_color_btn.setStyleSheet(f"background-color: {text_color}; border: 1px solid #666; min-width: 50px; min-height: 22px;")
            text_color_btn.setCursor(Qt.PointingHandCursor)
            text_color_btn.clicked.connect(lambda: _pick_color('text_color', text_color, text_color_btn))
            self.geometry_layout.addRow(t("文字颜色:", "Text color:"), text_color_btn)
        
        # 弧面设置（与单键参数面板一致，供弧面+文字贴合生成）
        curved_enabled_check = QCheckBox(t("启用弧面", "Enable curved surface"))
        curved_enabled_check.setChecked(getattr(geometry, 'curved_top_enabled', False))
        curved_enabled_check.stateChanged.connect(lambda v: self._on_geometry_changed('curved_top_enabled', v == Qt.Checked))
        self.curved_layout.addRow(t("启用弧面:", "Enable curved surface:"), curved_enabled_check)
        
        curved_x_row = QHBoxLayout()
        curved_x_check = QCheckBox(t("X方向", "X direction"))
        curved_x_check.setChecked(getattr(geometry, 'curved_top_x_enabled', False))
        curved_x_check.stateChanged.connect(lambda v: self._on_geometry_changed('curved_top_x_enabled', v == Qt.Checked))
        curved_x_row.addWidget(curved_x_check)
        curved_x_row.addWidget(QLabel(t("半径:", "Radius:")))
        curved_x_radius_spin = QDoubleSpinBox()
        curved_x_radius_spin.setRange(10.0, 1000.0)
        curved_x_radius_spin.setValue(getattr(geometry, 'curved_top_x_radius', 90.0))
        curved_x_radius_spin.setDecimals(1)
        curved_x_radius_spin.setSuffix(" mm")
        curved_x_radius_spin.valueChanged.connect(lambda v: self._on_geometry_changed('curved_top_x_radius', v))
        curved_x_row.addWidget(curved_x_radius_spin)
        self.curved_layout.addRow(t("X方向弧面:", "X direction curved surface:"), curved_x_row)
        
        curved_y_row = QHBoxLayout()
        curved_y_check = QCheckBox(t("Y方向", "Y direction"))
        curved_y_check.setChecked(getattr(geometry, 'curved_top_y_enabled', False))
        curved_y_check.stateChanged.connect(lambda v: self._on_geometry_changed('curved_top_y_enabled', v == Qt.Checked))
        curved_y_row.addWidget(curved_y_check)
        curved_y_row.addWidget(QLabel(t("半径:", "Radius:")))
        curved_y_radius_spin = QDoubleSpinBox()
        curved_y_radius_spin.setRange(10.0, 1000.0)
        curved_y_radius_spin.setValue(getattr(geometry, 'curved_top_y_radius', 90.0))
        curved_y_radius_spin.setDecimals(1)
        curved_y_radius_spin.setSuffix(" mm")
        curved_y_radius_spin.valueChanged.connect(lambda v: self._on_geometry_changed('curved_top_y_radius', v))
        curved_y_row.addWidget(curved_y_radius_spin)
        self.curved_layout.addRow(t("Y方向弧面:", "Y direction curved surface:"), curved_y_row)
        
        curved_direction_combo = QComboBox()
        curved_direction_combo.addItems([t("向上凸起", "Convex up"), t("向下凹陷", "Concave down")])
        curved_direction_combo.setCurrentText(
            t("向下凹陷", "Concave down") if getattr(geometry, 'curved_top_direction', 'convex') == 'concave' else t("向上凸起", "Convex up")
        )
        curved_direction_combo.currentTextChanged.connect(
            lambda text: self._on_geometry_changed('curved_top_direction', "concave" if text == t("向下凹陷", "Concave down") else "convex")
        )
        self.curved_layout.addRow(t("弧面方向:", "Curved surface direction:"), curved_direction_combo)
    
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
            
            browse_btn = QPushButton(t("浏览...", "Browse..."))
            browse_btn.clicked.connect(lambda checked=False, p=pos_idx, combo=font_combo: self._browse_font_for_position(p, combo))
            
            font_layout.addWidget(font_combo)
            font_layout.addWidget(browse_btn)
            pos_layout.addRow(t("字体:", "Font:"), font_layout)
            
            # 字体大小（调节增量来自设置）
            size_spin = QDoubleSpinBox()
            size_spin.setRange(1.0, 20.0)
            size_spin.setValue(style.size)
            size_spin.setDecimals(1)
            size_spin.setSuffix(" mm")
            if self.settings:
                size_spin.setSingleStep(self.settings.get_text_height_step())
            size_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_size(p, v))
            pos_layout.addRow(t("大小:", "Size:"), size_spin)
            
            # 深度（调节增量来自设置）
            depth_spin = QDoubleSpinBox()
            depth_spin.setRange(-2.0, 2.0)
            depth_spin.setValue(style.depth)
            depth_spin.setDecimals(2)
            depth_spin.setSuffix(" mm")
            if self.settings:
                depth_spin.setSingleStep(self.settings.get_text_depth_step())
            depth_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_depth(p, v))
            pos_layout.addRow(t("深度:", "Depth:"), depth_spin)
            
            # X偏移
            offset_x_spin = QDoubleSpinBox()
            offset_x_spin.setRange(-20.0, 20.0)
            offset_x_spin.setValue(style.offset_x)
            offset_x_spin.setDecimals(2)
            offset_x_spin.setSuffix(" mm")
            offset_x_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_offset_x(p, v))
            pos_layout.addRow(t("X偏移:", "X offset:"), offset_x_spin)
            
            # Y偏移
            offset_y_spin = QDoubleSpinBox()
            offset_y_spin.setRange(-20.0, 20.0)
            offset_y_spin.setValue(style.offset_y)
            offset_y_spin.setDecimals(2)
            offset_y_spin.setSuffix(" mm")
            offset_y_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_offset_y(p, v))
            pos_layout.addRow(t("Y偏移:", "Y offset:"), offset_y_spin)
            
            # 线宽（描边加粗，调节增量来自设置）
            stroke_width = getattr(style, 'stroke_width', 0.0)
            stroke_spin = QDoubleSpinBox()
            stroke_spin.setRange(0.0, 2.0)
            stroke_spin.setValue(stroke_width)
            stroke_spin.setDecimals(2)
            stroke_spin.setSuffix(" mm")
            if self.settings:
                stroke_spin.setSingleStep(self.settings.get_stroke_width_step())
            stroke_spin.setToolTip(t(">0 时向外加粗轮廓，避免细字体打印被切片软件跳过", ">0 to thicken outline, prevents thin fonts from being skipped by slicer"))
            stroke_spin.valueChanged.connect(lambda v, p=pos_idx: self._update_style_stroke_width(p, v))
            pos_layout.addRow(t("线宽:", "Stroke width:"), stroke_spin)
            
            # 样式：加粗、斜体、下划线
            style_row = QHBoxLayout()
            bold_check = QCheckBox(t("加粗", "Bold"))
            bold_check.setChecked(getattr(style, 'bold', False))
            bold_check.stateChanged.connect(lambda v, p=pos_idx: self._update_style_bool(p, 'bold', v == Qt.Checked))
            italic_check = QCheckBox(t("斜体", "Italic"))
            italic_check.setChecked(getattr(style, 'italic', False))
            italic_check.stateChanged.connect(lambda v, p=pos_idx: self._update_style_bool(p, 'italic', v == Qt.Checked))
            underline_check = QCheckBox(t("下划线", "Underline"))
            underline_check.setChecked(getattr(style, 'underline', False))
            underline_check.stateChanged.connect(lambda v, p=pos_idx: self._update_style_bool(p, 'underline', v == Qt.Checked))
            style_row.addWidget(bold_check)
            style_row.addWidget(italic_check)
            style_row.addWidget(underline_check)
            style_row.addStretch()
            pos_layout.addRow(t("样式:", "Style:"), style_row)
            
            pos_group.setLayout(pos_layout)
            self.style_layout.addWidget(pos_group)
            
            # 保存控件引用
            self.style_widgets[pos_idx] = {
                'font': font_combo,
                'size': size_spin,
                'depth': depth_spin,
                'offset_x': offset_x_spin,
                'offset_y': offset_y_spin,
                'stroke_width': stroke_spin
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
    
    def retranslateUi(self):
        """根据当前语言更新UI文案"""
        self.type_label.setText(t("未选择类型", "No type selected"))
        self.geometry_group.setTitle(t("几何参数（所有该类型按键共用）", "Geometry Parameters (shared by all keys of this type)"))
        self.curved_group.setTitle(t("弧面设置", "Curved Surface Settings"))
        self.style_group.setTitle(t("字符样式", "Character Styles"))
        self.save_btn.setText(t("保存并应用到所有该类型按键", "Save and apply to all keys of this type"))
    
    def _browse_font_for_position(self, pos_idx: int, combo: QComboBox):
        """为指定位置浏览字体文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t(f"选择字体文件 (位置{pos_idx})", f"Select Font File (Position {pos_idx})"),
            "",
            t("字体文件 (*.ttf *.otf *.ttc);;所有文件 (*.*)", "Font files (*.ttf *.otf *.ttc);;All files (*.*)")
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
    
    def _on_geometry_changed(self, attr: str, value):
        """几何参数改变（value 可为 float、bool、str，如弧面相关）"""
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
    
    def _update_style_stroke_width(self, pos_idx: int, value: float):
        """更新样式线宽"""
        if self.current_config:
            style = self.current_config.get_style_for_position(pos_idx, self.default_font_path)
            new_style = LegendStyle(
                font_path=style.font_path,
                size=style.size,
                offset_x=style.offset_x,
                offset_y=style.offset_y,
                depth=style.depth,
                rotation=getattr(style, 'rotation', 0.0),
                stroke_width=value,
                bold=getattr(style, 'bold', False),
                italic=getattr(style, 'italic', False),
                underline=getattr(style, 'underline', False)
            )
            self.current_config.set_style_for_position(pos_idx, new_style)
            self.config_changed.emit(self.current_config)
    
    def _update_style_bool(self, pos_idx: int, attr_name: str, value: bool):
        """更新样式布尔属性（加粗、斜体、下划线）"""
        if not self.current_config or attr_name not in ('bold', 'italic', 'underline'):
            return
        style = self.current_config.get_style_for_position(pos_idx, self.default_font_path)
        new_style = LegendStyle(
            font_path=style.font_path,
            size=style.size,
            offset_x=style.offset_x,
            offset_y=style.offset_y,
            depth=style.depth,
            rotation=getattr(style, 'rotation', 0.0),
            stroke_width=getattr(style, 'stroke_width', 0.0),
            bold=value if attr_name == 'bold' else getattr(style, 'bold', False),
            italic=value if attr_name == 'italic' else getattr(style, 'italic', False),
            underline=value if attr_name == 'underline' else getattr(style, 'underline', False)
        )
        self.current_config.set_style_for_position(pos_idx, new_style)
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
