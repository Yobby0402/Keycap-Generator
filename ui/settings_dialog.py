"""
设置对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QComboBox, QGridLayout, QFileDialog, QFormLayout)
from PyQt5.QtCore import Qt
from core.settings import Settings
from core.i18n import t
from utils.file_utils import get_system_fonts, get_font_name


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setMinimumWidth(400)
        self.setup_ui()
        self.retranslateUi()
        self.load_settings()
    
    def setup_ui(self):
        """设置UI（文案由 retranslateUi 设置）"""
        layout = QVBoxLayout(self)
        
        # 性能设置组
        self.perf_group = QGroupBox("")
        perf_layout = QVBoxLayout()
        
        self.auto_update_checkbox = QCheckBox("")
        self.auto_update_checkbox.setToolTip("")
        perf_layout.addWidget(self.auto_update_checkbox)
        
        self.perf_group.setLayout(perf_layout)
        layout.addWidget(self.perf_group)
        
        # 默认参数设置组（对单键设计和键盘参数对应项生效）
        self.default_params_group = QGroupBox("")
        default_params_layout = QVBoxLayout()
        self.form = QFormLayout()
        
        # 默认字体（可点击下拉选择，中文名优先显示）
        font_row = QHBoxLayout()
        self.default_font_combo = QComboBox()
        self.default_font_combo.setEditable(False)
        self._fill_font_combo()
        self.browse_font_btn = QPushButton("")
        self.browse_font_btn.clicked.connect(self._browse_default_font)
        font_row.addWidget(self.default_font_combo)
        font_row.addWidget(self.browse_font_btn)
        self._default_font_label = QLabel("")
        self.form.addRow(self._default_font_label, font_row)
        
        # 默认线宽、线宽调节增量
        self.default_stroke_width_spin = QDoubleSpinBox()
        self.default_stroke_width_spin.setRange(0.0, 2.0)
        self.default_stroke_width_spin.setDecimals(2)
        self.default_stroke_width_spin.setSuffix(" mm")
        self._stroke_width_label = QLabel("")
        self.form.addRow(self._stroke_width_label, self.default_stroke_width_spin)
        self.stroke_width_step_spin = QDoubleSpinBox()
        self.stroke_width_step_spin.setRange(0.01, 0.5)
        self.stroke_width_step_spin.setDecimals(2)
        self.stroke_width_step_spin.setSuffix(" mm")
        self._stroke_width_step_label = QLabel("")
        self.form.addRow(self._stroke_width_step_label, self.stroke_width_step_spin)
        
        # 默认壁厚、壁厚调节增量
        self.default_wall_spin = QDoubleSpinBox()
        self.default_wall_spin.setRange(0.5, 5.0)
        self.default_wall_spin.setDecimals(2)
        self.default_wall_spin.setSuffix(" mm")
        self._wall_label = QLabel("")
        self.form.addRow(self._wall_label, self.default_wall_spin)
        self.wall_step_spin = QDoubleSpinBox()
        self.wall_step_spin.setRange(0.05, 1.0)
        self.wall_step_spin.setDecimals(2)
        self.wall_step_spin.setSuffix(" mm")
        self._wall_step_label = QLabel("")
        self.form.addRow(self._wall_step_label, self.wall_step_spin)
        
        # 默认侧面斜角、调节增量
        self.default_side_angle_spin = QDoubleSpinBox()
        self.default_side_angle_spin.setRange(0.0, 30.0)
        self.default_side_angle_spin.setDecimals(1)
        self.default_side_angle_spin.setSuffix(" °")
        self._side_angle_label = QLabel("")
        self.form.addRow(self._side_angle_label, self.default_side_angle_spin)
        self.side_angle_step_spin = QDoubleSpinBox()
        self.side_angle_step_spin.setRange(0.1, 2.0)
        self.side_angle_step_spin.setDecimals(1)
        self.side_angle_step_spin.setSuffix(" °")
        self._side_angle_step_label = QLabel("")
        self.form.addRow(self._side_angle_step_label, self.side_angle_step_spin)
        
        # 边缘类型、边缘半径、边缘半径调节增量
        self.default_edge_mode_combo = QComboBox()
        self.default_edge_mode_combo.addItems([t("圆角", "Fillet"), t("45度斜角", "45° Chamfer")])
        self._edge_mode_label = QLabel("")
        self.form.addRow(self._edge_mode_label, self.default_edge_mode_combo)
        self.default_edge_radius_spin = QDoubleSpinBox()
        self.default_edge_radius_spin.setRange(0.0, 5.0)
        self.default_edge_radius_spin.setDecimals(2)
        self.default_edge_radius_spin.setSuffix(" mm")
        self._edge_radius_label = QLabel("")
        self.form.addRow(self._edge_radius_label, self.default_edge_radius_spin)
        self.edge_radius_step_spin = QDoubleSpinBox()
        self.edge_radius_step_spin.setRange(0.01, 0.5)
        self.edge_radius_step_spin.setDecimals(2)
        self.edge_radius_step_spin.setSuffix(" mm")
        self._edge_radius_step_label = QLabel("")
        self.form.addRow(self._edge_radius_step_label, self.edge_radius_step_spin)

        edge_apply_layout = QHBoxLayout()
        self.default_edge_outer_check = QCheckBox("")
        self.default_edge_inner_check = QCheckBox("")
        edge_apply_layout.addWidget(self.default_edge_outer_check)
        edge_apply_layout.addWidget(self.default_edge_inner_check)
        self._edge_apply_label = QLabel("")
        self.form.addRow(self._edge_apply_label, edge_apply_layout)

        edge_sides_layout = QGridLayout()
        self.default_edge_left_check = QCheckBox("")
        self.default_edge_right_check = QCheckBox("")
        self.default_edge_top_check = QCheckBox("")
        self.default_edge_bottom_check = QCheckBox("")
        edge_sides_layout.addWidget(self.default_edge_left_check, 0, 0)
        edge_sides_layout.addWidget(self.default_edge_right_check, 0, 1)
        edge_sides_layout.addWidget(self.default_edge_top_check, 1, 0)
        edge_sides_layout.addWidget(self.default_edge_bottom_check, 1, 1)
        self._edge_sides_label = QLabel("")
        self.form.addRow(self._edge_sides_label, edge_sides_layout)

        # 连接器/十字轴默认参数
        self._stem_cross_width_label = QLabel("")
        self.default_stem_cross_width_spin = QDoubleSpinBox()
        self.default_stem_cross_width_spin.setRange(0.5, 3.0)
        self.default_stem_cross_width_spin.setDecimals(1)
        self.default_stem_cross_width_spin.setSuffix(" mm")
        self.form.addRow(self._stem_cross_width_label, self.default_stem_cross_width_spin)
        self._stem_cross_length_label = QLabel("")
        self.default_stem_cross_length_spin = QDoubleSpinBox()
        self.default_stem_cross_length_spin.setRange(2.0, 8.0)
        self.default_stem_cross_length_spin.setDecimals(1)
        self.default_stem_cross_length_spin.setSuffix(" mm")
        self.form.addRow(self._stem_cross_length_label, self.default_stem_cross_length_spin)
        self._stem_height_label = QLabel("")
        self.default_stem_height_spin = QDoubleSpinBox()
        self.default_stem_height_spin.setRange(1.0, 10.0)
        self.default_stem_height_spin.setDecimals(1)
        self.default_stem_height_spin.setSuffix(" mm")
        self.form.addRow(self._stem_height_label, self.default_stem_height_spin)
        self._stem_cylinder_label = QLabel("")
        self.default_stem_cylinder_spin = QDoubleSpinBox()
        self.default_stem_cylinder_spin.setRange(3.0, 10.0)
        self.default_stem_cylinder_spin.setDecimals(1)
        self.default_stem_cylinder_spin.setSuffix(" mm")
        self.form.addRow(self._stem_cylinder_label, self.default_stem_cylinder_spin)
        self._top_thickness_label = QLabel("")
        self.default_top_thickness_spin = QDoubleSpinBox()
        self.default_top_thickness_spin.setRange(0.3, 5.0)
        self.default_top_thickness_spin.setDecimals(2)
        self.default_top_thickness_spin.setSuffix(" mm")
        self.form.addRow(self._top_thickness_label, self.default_top_thickness_spin)
        # 轴体类型、圆角半径、启用连接器
        self._stem_type_label = QLabel("")
        self.default_stem_type_combo = QComboBox()
        self.default_stem_type_combo.addItems(["MX", "Alps"])
        self.form.addRow(self._stem_type_label, self.default_stem_type_combo)
        self._stem_enabled_label = QLabel("")
        self.default_stem_enabled_check = QCheckBox("")
        self.default_stem_enabled_check.setChecked(True)
        self.form.addRow(self._stem_enabled_label, self.default_stem_enabled_check)
        self._corner_radius_label = QLabel("")
        self.default_corner_radius_spin = QDoubleSpinBox()
        self.default_corner_radius_spin.setRange(0.0, 5.0)
        self.default_corner_radius_spin.setDecimals(2)
        self.default_corner_radius_spin.setSuffix(" mm")
        self.form.addRow(self._corner_radius_label, self.default_corner_radius_spin)
        # 弧面默认
        self._curved_enabled_label = QLabel("")
        self.default_curved_enabled_check = QCheckBox("")
        self.form.addRow(self._curved_enabled_label, self.default_curved_enabled_check)
        self._curved_x_radius_label = QLabel("")
        self.default_curved_x_radius_spin = QDoubleSpinBox()
        self.default_curved_x_radius_spin.setRange(10.0, 1000.0)
        self.default_curved_x_radius_spin.setDecimals(1)
        self.default_curved_x_radius_spin.setSuffix(" mm")
        self.form.addRow(self._curved_x_radius_label, self.default_curved_x_radius_spin)
        self._curved_y_radius_label = QLabel("")
        self.default_curved_y_radius_spin = QDoubleSpinBox()
        self.default_curved_y_radius_spin.setRange(10.0, 1000.0)
        self.default_curved_y_radius_spin.setDecimals(1)
        self.default_curved_y_radius_spin.setSuffix(" mm")
        self.form.addRow(self._curved_y_radius_label, self.default_curved_y_radius_spin)
        self._curved_direction_label = QLabel("")
        self.default_curved_direction_combo = QComboBox()
        self.default_curved_direction_combo.addItems([t("向上凸起", "Convex up"), t("向下凹陷", "Concave down")])
        self.form.addRow(self._curved_direction_label, self.default_curved_direction_combo)
        # 卫星轴默认
        self._stabilizer_enabled_label = QLabel("")
        self.default_stabilizer_enabled_check = QCheckBox("")
        self.form.addRow(self._stabilizer_enabled_label, self.default_stabilizer_enabled_check)
        self._stabilizer_length_label = QLabel("")
        self.default_stabilizer_length_spin = QDoubleSpinBox()
        self.default_stabilizer_length_spin.setRange(10.0, 200.0)
        self.default_stabilizer_length_spin.setDecimals(1)
        self.default_stabilizer_length_spin.setSuffix(" mm")
        self.form.addRow(self._stabilizer_length_label, self.default_stabilizer_length_spin)
        self._stabilizer_cross_width_label = QLabel("")
        self.default_stabilizer_cross_width_spin = QDoubleSpinBox()
        self.default_stabilizer_cross_width_spin.setRange(0.5, 3.0)
        self.default_stabilizer_cross_width_spin.setDecimals(1)
        self.default_stabilizer_cross_width_spin.setSuffix(" mm")
        self.form.addRow(self._stabilizer_cross_width_label, self.default_stabilizer_cross_width_spin)
        self._stabilizer_cross_length_label = QLabel("")
        self.default_stabilizer_cross_length_spin = QDoubleSpinBox()
        self.default_stabilizer_cross_length_spin.setRange(2.0, 8.0)
        self.default_stabilizer_cross_length_spin.setDecimals(1)
        self.default_stabilizer_cross_length_spin.setSuffix(" mm")
        self.form.addRow(self._stabilizer_cross_length_label, self.default_stabilizer_cross_length_spin)
        self._stabilizer_cylinder_label = QLabel("")
        self.default_stabilizer_cylinder_spin = QDoubleSpinBox()
        self.default_stabilizer_cylinder_spin.setRange(2.0, 8.0)
        self.default_stabilizer_cylinder_spin.setDecimals(1)
        self.default_stabilizer_cylinder_spin.setSuffix(" mm")
        self.form.addRow(self._stabilizer_cylinder_label, self.default_stabilizer_cylinder_spin)
        self._stabilizer_depth_label = QLabel("")
        self.default_stabilizer_depth_spin = QDoubleSpinBox()
        self.default_stabilizer_depth_spin.setRange(2.0, 12.0)
        self.default_stabilizer_depth_spin.setDecimals(1)
        self.default_stabilizer_depth_spin.setSuffix(" mm")
        self.form.addRow(self._stabilizer_depth_label, self.default_stabilizer_depth_spin)
        
        # 文字参数
        self.default_text_height_spin = QDoubleSpinBox()
        self.default_text_height_spin.setRange(0.5, 20.0)
        self.default_text_height_spin.setDecimals(2)
        self.default_text_height_spin.setSuffix(" mm")
        self._text_height_label = QLabel("")
        self.form.addRow(self._text_height_label, self.default_text_height_spin)
        self.text_height_step_spin = QDoubleSpinBox()
        self.text_height_step_spin.setRange(0.05, 1.0)
        self.text_height_step_spin.setDecimals(2)
        self.text_height_step_spin.setSuffix(" mm")
        self._text_height_step_label = QLabel("")
        self.form.addRow(self._text_height_step_label, self.text_height_step_spin)
        self.default_text_depth_spin = QDoubleSpinBox()
        self.default_text_depth_spin.setRange(-2.0, 2.0)
        self.default_text_depth_spin.setDecimals(2)
        self.default_text_depth_spin.setSuffix(" mm")
        self._text_depth_label = QLabel("")
        self.form.addRow(self._text_depth_label, self.default_text_depth_spin)
        self.text_depth_step_spin = QDoubleSpinBox()
        self.text_depth_step_spin.setRange(0.01, 0.2)
        self.text_depth_step_spin.setDecimals(2)
        self.text_depth_step_spin.setSuffix(" mm")
        self._text_depth_step_label = QLabel("")
        self.form.addRow(self._text_depth_step_label, self.text_depth_step_spin)
        
        default_params_layout.addLayout(self.form)
        self.default_params_group.setLayout(default_params_layout)
        layout.addWidget(self.default_params_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def retranslateUi(self):
        """根据当前语言更新对话框文案"""
        self.setWindowTitle(t("设置", "Settings"))
        self.perf_group.setTitle(t("性能设置", "Performance"))
        self.auto_update_checkbox.setText(t("开启实时刷新 (修改参数或拖动时自动重新计算模型)", "Enable real-time refresh (auto-recalculate on parameter change or drag)"))
        self.auto_update_checkbox.setToolTip(t("开启后，修改参数或拖动文字结束后会自动重新生成模型。\n警告：复杂模型可能会导致卡顿。", "When enabled, model regenerates automatically after parameter changes or text drag.\nWarning: Complex models may cause lag."))
        self.default_params_group.setTitle(t("默认按键参数", "Default Key Parameters"))
        self._default_font_label.setText(t("默认字体:", "Default font:"))
        self.browse_font_btn.setText(t("浏览...", "Browse..."))
        self._stroke_width_label.setText(t("默认线宽:", "Default stroke width:"))
        self._stroke_width_step_label.setText(t("线宽调节增量:", "Stroke width step:"))
        self._wall_label.setText(t("默认壁厚:", "Default wall thickness:"))
        self._wall_step_label.setText(t("壁厚调节增量:", "Wall thickness step:"))
        self._side_angle_label.setText(t("默认侧面斜角:", "Default side angle:"))
        self._side_angle_step_label.setText(t("侧面斜角调节增量:", "Side angle step:"))
        self._edge_mode_label.setText(t("默认边缘类型:", "Default edge type:"))
        self._edge_radius_label.setText(t("默认边缘半径:", "Default edge radius:"))
        self._edge_radius_step_label.setText(t("边缘半径调节增量:", "Edge radius step:"))
        self._edge_apply_label.setText(t("边缘生效:", "Edge apply:"))
        self.default_edge_outer_check.setText(t("外侧边缘生效", "Outer edge"))
        self.default_edge_inner_check.setText(t("内侧边缘生效", "Inner edge"))
        self._edge_sides_label.setText(t("生效边:", "Active sides:"))
        self.default_edge_left_check.setText(t("左", "Left"))
        self.default_edge_right_check.setText(t("右", "Right"))
        self.default_edge_top_check.setText(t("上", "Top"))
        self.default_edge_bottom_check.setText(t("下", "Bottom"))
        self._stem_cross_width_label.setText(t("默认十字轴宽度:", "Default stem cross width:"))
        self._stem_cross_length_label.setText(t("默认十字轴长度:", "Default stem cross length:"))
        self._stem_height_label.setText(t("默认连接器深度:", "Default stem depth:"))
        self._stem_cylinder_label.setText(t("默认圆柱直径:", "Default cylinder diameter:"))
        self._top_thickness_label.setText(t("默认顶面厚度:", "Default top thickness:"))
        self._stem_type_label.setText(t("默认轴体类型:", "Default stem type:"))
        self._stem_enabled_label.setText(t("默认启用连接器:", "Default enable stem:"))
        self._corner_radius_label.setText(t("默认圆角半径:", "Default corner radius:"))
        self._curved_enabled_label.setText(t("默认启用弧面:", "Default enable curved surface:"))
        self._curved_x_radius_label.setText(t("默认弧面X半径:", "Default curved X radius:"))
        self._curved_y_radius_label.setText(t("默认弧面Y半径:", "Default curved Y radius:"))
        self._curved_direction_label.setText(t("默认弧面方向:", "Default curved direction:"))
        cur_dir = self.default_curved_direction_combo.currentText()
        self.default_curved_direction_combo.clear()
        self.default_curved_direction_combo.addItems([t("向上凸起", "Convex up"), t("向下凹陷", "Concave down")])
        if cur_dir in [t("向上凸起", "Convex up"), t("向下凹陷", "Concave down")]:
            self.default_curved_direction_combo.setCurrentText(cur_dir)
        else:
            self.default_curved_direction_combo.setCurrentText(t("向上凸起", "Convex up"))
        self._stabilizer_enabled_label.setText(t("默认启用卫星轴:", "Default enable stabilizer:"))
        self._stabilizer_length_label.setText(t("默认卫星轴长度:", "Default stabilizer length:"))
        self._stabilizer_cross_width_label.setText(t("默认卫星轴十字宽度:", "Default stabilizer cross width:"))
        self._stabilizer_cross_length_label.setText(t("默认卫星轴十字长度:", "Default stabilizer cross length:"))
        self._stabilizer_cylinder_label.setText(t("默认卫星轴圆柱直径:", "Default stabilizer cylinder diam.:"))
        self._stabilizer_depth_label.setText(t("默认卫星轴连接器深度:", "Default stabilizer depth:"))
        self._text_height_label.setText(t("默认文字高度:", "Default text height:"))
        self._text_height_step_label.setText(t("文字高度调节增量:", "Text height step:"))
        self._text_depth_label.setText(t("默认文字深度:", "Default text depth:"))
        self._text_depth_step_label.setText(t("文字深度调节增量:", "Text depth step:"))
        self.ok_btn.setText(t("确定", "OK"))
        self.cancel_btn.setText(t("取消", "Cancel"))
        # 更新边缘类型下拉（需重新设置项）
        current = self.default_edge_mode_combo.currentText()
        self.default_edge_mode_combo.clear()
        self.default_edge_mode_combo.addItems([t("圆角", "Fillet"), t("45度斜角", "45° Chamfer")])
        if current in [t("圆角", "Fillet"), t("45度斜角", "45° Chamfer")]:
            self.default_edge_mode_combo.setCurrentText(current)
        elif current == "圆角" or current == "Fillet":
            self.default_edge_mode_combo.setCurrentText(t("圆角", "Fillet"))
        elif current == "45度斜角" or current == "45° Chamfer":
            self.default_edge_mode_combo.setCurrentText(t("45度斜角", "45° Chamfer"))
    
    def _fill_font_combo(self):
        """填充默认字体下拉框，显示名用 get_font_name（中文优先）"""
        self.default_font_combo.clear()
        self.default_font_combo.addItem(t("未设置", "Not set"), None)
        try:
            for font_path in get_system_fonts():
                name = get_font_name(font_path)
                self.default_font_combo.addItem(name, font_path)
        except Exception as e:
            print(f"加载系统字体列表时出错: {e}")
    
    def _browse_default_font(self):
        """浏览选择默认字体文件，选中后加入下拉并设为当前项"""
        path, _ = QFileDialog.getOpenFileName(
            self, t("选择默认字体", "Select Default Font"),
            "", t("字体文件 (*.ttf *.otf *.ttc);;所有文件 (*.*)", "Font files (*.ttf *.otf *.ttc);;All files (*.*)")
        )
        if not path:
            return
        for i in range(self.default_font_combo.count()):
            if self.default_font_combo.itemData(i) == path:
                self.default_font_combo.setCurrentIndex(i)
                return
        name = get_font_name(path)
        self.default_font_combo.addItem(name, path)
        self.default_font_combo.setCurrentIndex(self.default_font_combo.count() - 1)
    
    def load_settings(self):
        """加载设置"""
        self.auto_update_checkbox.setChecked(self.settings.get_auto_update())
        
        # 默认字体：在列表中按路径找对应项并选中；若未在列表中则插入一项并选中
        fp = self.settings.get_default_font_path()
        idx = -1
        for i in range(self.default_font_combo.count()):
            if self.default_font_combo.itemData(i) == fp:
                idx = i
                break
        if idx >= 0:
            self.default_font_combo.setCurrentIndex(idx)
        elif fp:
            self.default_font_combo.addItem(get_font_name(fp), fp)
            self.default_font_combo.setCurrentIndex(self.default_font_combo.count() - 1)
        else:
            self.default_font_combo.setCurrentIndex(0)
        
        # 线宽
        self.default_stroke_width_spin.setValue(self.settings.get_default_stroke_width())
        self.stroke_width_step_spin.setValue(self.settings.get_stroke_width_step())
        # 壁厚
        self.default_wall_spin.setValue(self.settings.get_default_wall_thickness())
        self.wall_step_spin.setValue(self.settings.get_wall_thickness_step())
        # 侧面斜角
        self.default_side_angle_spin.setValue(self.settings.get_default_side_angle())
        self.side_angle_step_spin.setValue(self.settings.get_side_angle_step())
        # 边缘
        mode_map = {"fillet": t("圆角", "Fillet"), "chamfer": t("45度斜角", "45° Chamfer")}
        self.default_edge_mode_combo.setCurrentText(mode_map.get(
            self.settings.get_default_edge_profile_mode(), t("圆角", "Fillet")))
        self.default_edge_radius_spin.setValue(self.settings.get_default_edge_profile_radius())
        self.edge_radius_step_spin.setValue(self.settings.get_edge_radius_step())
        self.default_edge_outer_check.setChecked(self.settings.get_default_edge_profile_outer())
        self.default_edge_inner_check.setChecked(self.settings.get_default_edge_profile_inner())
        self.default_edge_left_check.setChecked(self.settings.get_default_edge_profile_left())
        self.default_edge_right_check.setChecked(self.settings.get_default_edge_profile_right())
        self.default_edge_top_check.setChecked(self.settings.get_default_edge_profile_top())
        self.default_edge_bottom_check.setChecked(self.settings.get_default_edge_profile_bottom())
        # 连接器/十字轴、顶面厚度
        self.default_stem_cross_width_spin.setValue(self.settings.get_default_stem_cross_width())
        self.default_stem_cross_length_spin.setValue(self.settings.get_default_stem_cross_length())
        self.default_stem_height_spin.setValue(self.settings.get_default_stem_height())
        self.default_stem_cylinder_spin.setValue(self.settings.get_default_stem_cylinder_diameter())
        self.default_top_thickness_spin.setValue(self.settings.get_default_top_thickness())
        self.default_stem_type_combo.setCurrentText(self.settings.get_default_stem_type())
        self.default_stem_enabled_check.setChecked(self.settings.get_default_stem_enabled())
        self.default_corner_radius_spin.setValue(self.settings.get_default_corner_radius())
        self.default_curved_enabled_check.setChecked(self.settings.get_default_curved_top_enabled())
        self.default_curved_x_radius_spin.setValue(self.settings.get_default_curved_top_x_radius())
        self.default_curved_y_radius_spin.setValue(self.settings.get_default_curved_top_y_radius())
        self.default_curved_direction_combo.setCurrentText(
            t("向下凹陷", "Concave down") if self.settings.get_default_curved_top_direction() == "concave" else t("向上凸起", "Convex up"))
        self.default_stabilizer_enabled_check.setChecked(self.settings.get_default_stabilizer_enabled())
        self.default_stabilizer_length_spin.setValue(self.settings.get_default_stabilizer_length())
        self.default_stabilizer_cross_width_spin.setValue(self.settings.get_default_stabilizer_cross_width())
        self.default_stabilizer_cross_length_spin.setValue(self.settings.get_default_stabilizer_cross_length())
        self.default_stabilizer_cylinder_spin.setValue(self.settings.get_default_stabilizer_cylinder_diameter())
        self.default_stabilizer_depth_spin.setValue(self.settings.get_default_stabilizer_depth())
        # 文字参数
        self.default_text_height_spin.setValue(self.settings.get_default_text_height())
        self.text_height_step_spin.setValue(self.settings.get_text_height_step())
        self.default_text_depth_spin.setValue(self.settings.get_default_text_depth())
        self.text_depth_step_spin.setValue(self.settings.get_text_depth_step())
    
    def save_settings(self):
        """保存设置"""
        self.settings.set_auto_update(self.auto_update_checkbox.isChecked())
        
        path = self.default_font_combo.currentData()
        self.settings.set_default_font_path(path)
        self.settings.set_default_stroke_width(self.default_stroke_width_spin.value())
        self.settings.set_stroke_width_step(self.stroke_width_step_spin.value())
        self.settings.set_default_wall_thickness(self.default_wall_spin.value())
        self.settings.set_wall_thickness_step(self.wall_step_spin.value())
        self.settings.set_default_side_angle(self.default_side_angle_spin.value())
        self.settings.set_side_angle_step(self.side_angle_step_spin.value())
        
        mode_map = {t("圆角", "Fillet"): "fillet", t("45度斜角", "45° Chamfer"): "chamfer"}
        self.settings.set_default_edge_profile_mode(
            mode_map.get(self.default_edge_mode_combo.currentText(), "fillet"))
        self.settings.set_default_edge_profile_radius(self.default_edge_radius_spin.value())
        self.settings.set_edge_radius_step(self.edge_radius_step_spin.value())
        self.settings.set_default_edge_profile_outer(self.default_edge_outer_check.isChecked())
        self.settings.set_default_edge_profile_inner(self.default_edge_inner_check.isChecked())
        self.settings.set_default_edge_profile_left(self.default_edge_left_check.isChecked())
        self.settings.set_default_edge_profile_right(self.default_edge_right_check.isChecked())
        self.settings.set_default_edge_profile_top(self.default_edge_top_check.isChecked())
        self.settings.set_default_edge_profile_bottom(self.default_edge_bottom_check.isChecked())
        self.settings.set_default_stem_cross_width(self.default_stem_cross_width_spin.value())
        self.settings.set_default_stem_cross_length(self.default_stem_cross_length_spin.value())
        self.settings.set_default_stem_height(self.default_stem_height_spin.value())
        self.settings.set_default_stem_cylinder_diameter(self.default_stem_cylinder_spin.value())
        self.settings.set_default_top_thickness(self.default_top_thickness_spin.value())
        self.settings.set_default_stem_type(self.default_stem_type_combo.currentText())
        self.settings.set_default_stem_enabled(self.default_stem_enabled_check.isChecked())
        self.settings.set_default_corner_radius(self.default_corner_radius_spin.value())
        self.settings.set_default_curved_top_enabled(self.default_curved_enabled_check.isChecked())
        self.settings.set_default_curved_top_x_radius(self.default_curved_x_radius_spin.value())
        self.settings.set_default_curved_top_y_radius(self.default_curved_y_radius_spin.value())
        self.settings.set_default_curved_top_direction(
            "concave" if self.default_curved_direction_combo.currentText() == t("向下凹陷", "Concave down") else "convex")
        self.settings.set_default_stabilizer_enabled(self.default_stabilizer_enabled_check.isChecked())
        self.settings.set_default_stabilizer_length(self.default_stabilizer_length_spin.value())
        self.settings.set_default_stabilizer_cross_width(self.default_stabilizer_cross_width_spin.value())
        self.settings.set_default_stabilizer_cross_length(self.default_stabilizer_cross_length_spin.value())
        self.settings.set_default_stabilizer_cylinder_diameter(self.default_stabilizer_cylinder_spin.value())
        self.settings.set_default_stabilizer_depth(self.default_stabilizer_depth_spin.value())
        
        self.settings.set_default_text_height(self.default_text_height_spin.value())
        self.settings.set_text_height_step(self.text_height_step_spin.value())
        self.settings.set_default_text_depth(self.default_text_depth_spin.value())
        self.settings.set_text_depth_step(self.text_depth_step_spin.value())
    
    def accept(self):
        """确定按钮"""
        self.save_settings()
        super().accept()
