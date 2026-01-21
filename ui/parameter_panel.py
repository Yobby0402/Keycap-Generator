"""
参数输入面板
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
                             QGroupBox, QFileDialog, QMessageBox, QCheckBox,
                             QFormLayout, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from core.parameters import KeycapParameters
from core.keycap_presets import (STANDARD_KEY_SIZES, KEYCAP_HEIGHT_PROFILES,
                                 get_key_size_mm, get_keycap_height, u_to_mm)
from utils.file_utils import get_system_fonts, get_font_name


class ParameterPanel(QWidget):
    """参数输入面板"""
    
    # 信号：参数改变时发出
    parameters_changed = pyqtSignal(KeycapParameters)
    # 信号：插入文字
    insert_text_signal = pyqtSignal(str, float)  # (text, font_size)
    
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.params = KeycapParameters()
        self.settings = settings
        self.setup_ui()
        self.load_system_fonts()
        if self.settings:
            self.load_default_parameters()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 字体选择组
        font_group = QGroupBox("字体设置")
        font_layout = QVBoxLayout()
        
        # 字体选择
        font_select_layout = QHBoxLayout()
        font_select_layout.addWidget(QLabel("字体:"))
        self.font_combo = QComboBox()
        self.font_combo.setEditable(False)
        self.font_combo.currentIndexChanged.connect(self.on_font_changed)
        font_select_layout.addWidget(self.font_combo)
        
        self.browse_font_btn = QPushButton("浏览...")
        self.browse_font_btn.clicked.connect(self.browse_font_file)
        font_select_layout.addWidget(self.browse_font_btn)
        font_layout.addLayout(font_select_layout)
        
        # 字母输入和插入按钮
        letter_layout = QHBoxLayout()
        letter_layout.addWidget(QLabel("字母:"))
        self.letter_edit = QLineEdit("A")
        self.letter_edit.setMaxLength(1)
        self.letter_edit.textChanged.connect(self.on_parameter_changed)
        letter_layout.addWidget(self.letter_edit)
        
        # 插入文字按钮
        self.insert_text_btn = QPushButton("插入")
        self.insert_text_btn.clicked.connect(self.on_insert_text_clicked)
        letter_layout.addWidget(self.insert_text_btn)
        font_layout.addLayout(letter_layout)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # 按键尺寸预设组
        size_preset_group = QGroupBox("按键尺寸预设")
        size_preset_layout = QVBoxLayout()
        
        # 使用u单位复选框
        self.use_u_checkbox = QCheckBox("使用标准单位 (u)")
        self.use_u_checkbox.setChecked(False)
        self.use_u_checkbox.stateChanged.connect(self.on_u_units_changed)
        size_preset_layout.addWidget(self.use_u_checkbox)
        
        # 标准尺寸选择
        size_select_layout = QHBoxLayout()
        size_select_layout.addWidget(QLabel("标准尺寸:"))
        self.size_preset_combo = QComboBox()
        self.size_preset_combo.addItems(list(STANDARD_KEY_SIZES.keys()))
        self.size_preset_combo.currentTextChanged.connect(self.on_size_preset_changed)
        size_select_layout.addWidget(self.size_preset_combo)
        size_preset_layout.addLayout(size_select_layout)
        
        size_preset_group.setLayout(size_preset_layout)
        layout.addWidget(size_preset_group)
        
        # 按键尺寸组
        size_group = QGroupBox("按键尺寸")
        size_layout = QVBoxLayout()
        
        # 宽度
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("宽度:"))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1.0, 200.0)
        self.width_spin.setValue(18.0)
        self.width_spin.setDecimals(2)
        self.width_spin.setSuffix(" mm")
        self.width_spin.valueChanged.connect(self.on_parameter_changed)
        width_layout.addWidget(self.width_spin)
        
        self.width_u_spin = QDoubleSpinBox()
        self.width_u_spin.setRange(0.25, 10.0)
        self.width_u_spin.setValue(1.0)
        self.width_u_spin.setDecimals(2)
        self.width_u_spin.setSuffix(" u")
        self.width_u_spin.setVisible(False)
        self.width_u_spin.valueChanged.connect(self.on_width_u_changed)
        width_layout.addWidget(self.width_u_spin)
        size_layout.addLayout(width_layout)
        
        # 高度
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("高度:"))
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1.0, 200.0)
        self.height_spin.setValue(18.0)
        self.height_spin.setDecimals(2)
        self.height_spin.setSuffix(" mm")
        self.height_spin.valueChanged.connect(self.on_parameter_changed)
        height_layout.addWidget(self.height_spin)
        
        self.height_u_spin = QDoubleSpinBox()
        self.height_u_spin.setRange(0.25, 10.0)
        self.height_u_spin.setValue(1.0)
        self.height_u_spin.setDecimals(2)
        self.height_u_spin.setSuffix(" u")
        self.height_u_spin.setVisible(False)
        self.height_u_spin.valueChanged.connect(self.on_height_u_changed)
        height_layout.addWidget(self.height_u_spin)
        size_layout.addLayout(height_layout)
        
        # 深度（键帽高度）
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("键帽高度:"))
        
        # 高度预设选择
        self.height_profile_combo = QComboBox()
        self.height_profile_combo.addItems(list(KEYCAP_HEIGHT_PROFILES.keys()))
        self.height_profile_combo.setCurrentText("Cherry高度")
        self.height_profile_combo.currentTextChanged.connect(self.on_height_profile_changed)
        depth_layout.addWidget(self.height_profile_combo)
        
        # 行号选择
        self.row_combo = QComboBox()
        self.row_combo.addItems(["R1", "R2", "R3", "R4"])
        self.row_combo.setCurrentText("R3")
        self.row_combo.currentTextChanged.connect(self.on_row_changed)
        depth_layout.addWidget(self.row_combo)
        
        # 手动输入深度
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(1.0, 50.0)
        self.depth_spin.setValue(8.0)
        self.depth_spin.setDecimals(2)
        self.depth_spin.setSuffix(" mm")
        self.depth_spin.valueChanged.connect(self.on_parameter_changed)
        depth_layout.addWidget(self.depth_spin)
        size_layout.addLayout(depth_layout)
        
        # 壁厚
        wall_layout = QHBoxLayout()
        wall_layout.addWidget(QLabel("壁厚:"))
        self.wall_spin = QDoubleSpinBox()
        self.wall_spin.setRange(0.5, 5.0)
        self.wall_spin.setValue(1.0)
        self.wall_spin.setDecimals(2)
        self.wall_spin.setSuffix(" mm")
        self.wall_spin.valueChanged.connect(self.on_parameter_changed)
        wall_layout.addWidget(self.wall_spin)
        size_layout.addLayout(wall_layout)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 斜角组
        angle_group = QGroupBox("斜角 (度)")
        angle_layout = QVBoxLayout()

        # 侧面斜角
        side_angle_layout = QHBoxLayout()
        side_angle_layout.addWidget(QLabel("侧面斜角:"))
        self.side_angle_spin = QDoubleSpinBox()
        self.side_angle_spin.setRange(0.0, 30.0)
        self.side_angle_spin.setValue(0.0)
        self.side_angle_spin.setDecimals(1)
        self.side_angle_spin.setSuffix(" °")
        self.side_angle_spin.valueChanged.connect(self.on_parameter_changed)
        side_angle_layout.addWidget(self.side_angle_spin)
        angle_layout.addLayout(side_angle_layout)
        
        angle_group.setLayout(angle_layout)
        layout.addWidget(angle_group)
        
        # 边缘形状设置组
        edge_group = QGroupBox("边缘形状设置")
        edge_layout = QVBoxLayout()

        # 边缘类型
        edge_mode_layout = QHBoxLayout()
        edge_mode_layout.addWidget(QLabel("类型:"))
        self.edge_mode_combo = QComboBox()
        self.edge_mode_combo.addItems(["圆角", "45度斜角"])
        self.edge_mode_combo.currentTextChanged.connect(self.on_parameter_changed)
        edge_mode_layout.addWidget(self.edge_mode_combo)
        edge_layout.addLayout(edge_mode_layout)

        # 边缘半径
        edge_radius_layout = QHBoxLayout()
        edge_radius_layout.addWidget(QLabel("半径:"))
        self.edge_radius_spin = QDoubleSpinBox()
        self.edge_radius_spin.setRange(0.0, 5.0)
        self.edge_radius_spin.setValue(0.0)
        self.edge_radius_spin.setDecimals(2)
        self.edge_radius_spin.setSuffix(" mm")
        self.edge_radius_spin.setMinimumHeight(25)
        self.edge_radius_spin.valueChanged.connect(self.on_parameter_changed)
        edge_radius_layout.addWidget(self.edge_radius_spin)
        edge_layout.addLayout(edge_radius_layout)

        # 作用边缘（外侧/内侧）
        edge_apply_layout = QHBoxLayout()
        self.edge_outer_check = QCheckBox("外侧边缘")
        self.edge_outer_check.setChecked(True)
        self.edge_outer_check.stateChanged.connect(self.on_parameter_changed)
        self.edge_inner_check = QCheckBox("内侧边缘")
        self.edge_inner_check.setChecked(False)
        self.edge_inner_check.stateChanged.connect(self.on_parameter_changed)
        edge_apply_layout.addWidget(self.edge_outer_check)
        edge_apply_layout.addWidget(self.edge_inner_check)
        edge_layout.addLayout(edge_apply_layout)

        # 生效边（左右上下）
        edge_sides_layout = QGridLayout()
        edge_sides_layout.addWidget(QLabel("生效边:"), 0, 0)
        self.edge_left_check = QCheckBox("左")
        self.edge_right_check = QCheckBox("右")
        self.edge_top_check = QCheckBox("上")
        self.edge_bottom_check = QCheckBox("下")
        for chk in (self.edge_left_check, self.edge_right_check, self.edge_top_check, self.edge_bottom_check):
            chk.setChecked(True)
            chk.stateChanged.connect(self.on_parameter_changed)
        edge_sides_layout.addWidget(self.edge_left_check, 0, 1)
        edge_sides_layout.addWidget(self.edge_right_check, 0, 2)
        edge_sides_layout.addWidget(self.edge_top_check, 1, 1)
        edge_sides_layout.addWidget(self.edge_bottom_check, 1, 2)
        edge_layout.addLayout(edge_sides_layout)

        edge_group.setLayout(edge_layout)
        layout.addWidget(edge_group)
        
        # 文字参数组
        text_group = QGroupBox("文字参数 (mm)")
        text_layout = QVBoxLayout()
        
        # 文字高度
        text_height_layout = QHBoxLayout()
        text_height_layout.addWidget(QLabel("文字高度:"))
        self.text_height_spin = QDoubleSpinBox()
        self.text_height_spin.setRange(0.5, 20.0)
        self.text_height_spin.setValue(3.0)
        self.text_height_spin.setDecimals(2)
        self.text_height_spin.setSuffix(" mm")
        self.text_height_spin.valueChanged.connect(self.on_parameter_changed)
        text_height_layout.addWidget(self.text_height_spin)
        text_layout.addLayout(text_height_layout)
        
        # 文字深度
        text_depth_layout = QHBoxLayout()
        text_depth_layout.addWidget(QLabel("文字深度:"))
        self.text_depth_spin = QDoubleSpinBox()
        self.text_depth_spin.setRange(-2.0, 2.0)
        self.text_depth_spin.setValue(0.5)
        self.text_depth_spin.setDecimals(2)
        self.text_depth_spin.setSuffix(" mm")
        self.text_depth_spin.setToolTip("正值表示凹陷，负值表示凸起")
        self.text_depth_spin.valueChanged.connect(self.on_parameter_changed)
        text_depth_layout.addWidget(self.text_depth_spin)
        text_layout.addLayout(text_depth_layout)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # 轴体类型和连接器设置
        stem_group = QGroupBox("连接器设置")
        stem_layout = QVBoxLayout()
        
        # 启用连接器
        self.stem_enabled_checkbox = QCheckBox("启用连接器")
        self.stem_enabled_checkbox.setChecked(True)
        self.stem_enabled_checkbox.stateChanged.connect(self.on_parameter_changed)
        stem_layout.addWidget(self.stem_enabled_checkbox)
        
        # 轴体类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.stem_combo = QComboBox()
        self.stem_combo.addItems(["MX", "Alps"])
        self.stem_combo.setCurrentText("MX")
        self.stem_combo.currentTextChanged.connect(self.on_parameter_changed)
        type_layout.addWidget(self.stem_combo)
        stem_layout.addLayout(type_layout)
        
        # 连接器深度
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("深度:"))
        self.stem_height_spin = QDoubleSpinBox()
        self.stem_height_spin.setRange(1.0, 10.0)
        self.stem_height_spin.setValue(4.0)
        self.stem_height_spin.setDecimals(1)
        self.stem_height_spin.setSuffix(" mm")
        self.stem_height_spin.valueChanged.connect(self.on_parameter_changed)
        depth_layout.addWidget(self.stem_height_spin)
        stem_layout.addLayout(depth_layout)
        
        # 圆柱直径
        cylinder_layout = QHBoxLayout()
        cylinder_layout.addWidget(QLabel("圆柱直径:"))
        self.stem_cylinder_spin = QDoubleSpinBox()
        self.stem_cylinder_spin.setRange(3.0, 10.0)
        self.stem_cylinder_spin.setValue(5.4)
        self.stem_cylinder_spin.setDecimals(1)
        self.stem_cylinder_spin.setSuffix(" mm")
        self.stem_cylinder_spin.valueChanged.connect(self.on_parameter_changed)
        cylinder_layout.addWidget(self.stem_cylinder_spin)
        stem_layout.addLayout(cylinder_layout)
        
        # 十字尺寸
        cross_layout = QHBoxLayout()
        cross_layout.addWidget(QLabel("十字:"))
        self.stem_cross_length_spin = QDoubleSpinBox()
        self.stem_cross_length_spin.setRange(2.0, 8.0)
        self.stem_cross_length_spin.setValue(4.0)
        self.stem_cross_length_spin.setDecimals(1)
        self.stem_cross_length_spin.setSuffix(" mm")
        self.stem_cross_length_spin.valueChanged.connect(self.on_parameter_changed)
        cross_layout.addWidget(QLabel("长度"))
        cross_layout.addWidget(self.stem_cross_length_spin)
        
        self.stem_cross_width_spin = QDoubleSpinBox()
        self.stem_cross_width_spin.setRange(0.5, 3.0)
        self.stem_cross_width_spin.setValue(1.0)
        self.stem_cross_width_spin.setDecimals(1)
        self.stem_cross_width_spin.setSuffix(" mm")
        self.stem_cross_width_spin.valueChanged.connect(self.on_parameter_changed)
        cross_layout.addWidget(QLabel("宽度"))
        cross_layout.addWidget(self.stem_cross_width_spin)
        stem_layout.addLayout(cross_layout)
        
        stem_group.setLayout(stem_layout)
        layout.addWidget(stem_group)

        # 卫星轴设置（单键）
        stabilizer_group = QGroupBox("卫星轴设置")
        stabilizer_layout = QVBoxLayout()

        self.stabilizer_enabled_checkbox = QCheckBox("启用卫星轴连接器")
        self.stabilizer_enabled_checkbox.setChecked(False)
        self.stabilizer_enabled_checkbox.stateChanged.connect(self.on_parameter_changed)
        stabilizer_layout.addWidget(self.stabilizer_enabled_checkbox)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.stabilizer_type_combo = QComboBox()
        self.stabilizer_type_combo.addItem("自定义", -1)
        self.stabilizer_type_combo.addItem("2u (标准)", 2.0)
        self.stabilizer_type_combo.addItem("6.25u (空格键)", 6.25)
        self.stabilizer_type_combo.currentIndexChanged.connect(self._on_stabilizer_type_changed)
        type_layout.addWidget(self.stabilizer_type_combo)
        stabilizer_layout.addLayout(type_layout)

        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("长度:"))
        self.stabilizer_length_spin = QDoubleSpinBox()
        self.stabilizer_length_spin.setRange(10.0, 200.0)
        self.stabilizer_length_spin.setValue(50.0)
        self.stabilizer_length_spin.setDecimals(1)
        self.stabilizer_length_spin.setSuffix(" mm")
        self.stabilizer_length_spin.valueChanged.connect(self._on_stabilizer_length_changed)
        length_layout.addWidget(self.stabilizer_length_spin)
        stabilizer_layout.addLayout(length_layout)

        stabilizer_group.setLayout(stabilizer_layout)
        layout.addWidget(stabilizer_group)
        
        # 按钮
        self.generate_btn = QPushButton("生成模型")
        self.generate_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.generate_btn)
        
        layout.addStretch()
    
    def load_system_fonts(self):
        """加载系统字体"""
        try:
            fonts = get_system_fonts()
            for font_path in fonts:  # 加载所有字体
                font_name = get_font_name(font_path)
                self.font_combo.addItem(font_name, font_path)
        except Exception as e:
            print(f"加载系统字体时出错: {e}")
    
    def browse_font_file(self):
        """浏览字体文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择字体文件",
            "",
            "字体文件 (*.ttf *.otf *.ttc);;所有文件 (*.*)"
        )
        
        if file_path:
            font_name = get_font_name(file_path)
            # 添加到组合框
            self.font_combo.addItem(font_name, file_path)
            self.font_combo.setCurrentIndex(self.font_combo.count() - 1)
    
    def on_font_changed(self, index: int):
        """字体改变时的处理"""
        if index >= 0:
            font_path = self.font_combo.itemData(index)
            if font_path:
                self.params.font_path = font_path
                print(f"字体已选择: {font_path}")
            else:
                # 如果没有数据，尝试从字体名称获取
                font_name = self.font_combo.currentText()
                print(f"警告：字体路径为空，字体名称: {font_name}")
            self.on_parameter_changed()
    
    def on_u_units_changed(self, state):
        """u单位切换"""
        use_u = state == Qt.Checked
        self.params.use_u_units = use_u
        
        # 切换显示
        self.width_spin.setVisible(not use_u)
        self.height_spin.setVisible(not use_u)
        self.width_u_spin.setVisible(use_u)
        self.height_u_spin.setVisible(use_u)
        
        if use_u:
            # 转换当前值到u单位
            from core.keycap_presets import mm_to_u
            self.width_u_spin.setValue(mm_to_u(self.params.key_width))
            self.height_u_spin.setValue(mm_to_u(self.params.key_height))
        else:
            # 转换u单位到mm
            from core.keycap_presets import u_to_mm
            self.width_spin.setValue(u_to_mm(self.width_u_spin.value()))
            self.height_spin.setValue(u_to_mm(self.height_u_spin.value()))
        
        self.on_parameter_changed()
    
    def on_width_u_changed(self, value):
        """宽度u单位改变"""
        from core.keycap_presets import u_to_mm
        self.params.key_width = u_to_mm(value)
        self.params.key_width_u = value
        if not self.use_u_checkbox.isChecked():
            self.width_spin.setValue(self.params.key_width)
        self.on_parameter_changed()
    
    def on_height_u_changed(self, value):
        """高度u单位改变"""
        from core.keycap_presets import u_to_mm
        self.params.key_height = u_to_mm(value)
        self.params.key_height_u = value
        if not self.use_u_checkbox.isChecked():
            self.height_spin.setValue(self.params.key_height)
        self.on_parameter_changed()
    
    def on_size_preset_changed(self, size_name: str):
        """标准尺寸预设改变"""
        width_mm, height_mm = get_key_size_mm(size_name)
        self.params.key_width = width_mm
        self.params.key_height = height_mm
        
        if self.use_u_checkbox.isChecked():
            from core.keycap_presets import mm_to_u
            self.width_u_spin.setValue(mm_to_u(width_mm))
            self.height_u_spin.setValue(mm_to_u(height_mm))
        else:
            self.width_spin.setValue(width_mm)
            self.height_spin.setValue(height_mm)
        
        self.on_parameter_changed()
    
    def on_height_profile_changed(self, profile_name: str):
        """高度预设改变"""
        self.params.height_profile = profile_name
        row = self.row_combo.currentText()
        height = get_keycap_height(profile_name, row)
        self.params.key_depth = height
        self.depth_spin.setValue(height)
        self.on_parameter_changed()
    
    def on_row_changed(self, row: str):
        """行号改变"""
        self.params.keycap_row = row
        profile = self.height_profile_combo.currentText()
        height = get_keycap_height(profile, row)
        self.params.key_depth = height
        self.depth_spin.setValue(height)
        self.on_parameter_changed()

    def _on_stabilizer_type_changed(self, index: int):
        """卫星轴类型改变"""
        value = self.stabilizer_type_combo.currentData()
        if value is None or value <= 0:
            return
        try:
            from core.keycap_presets import u_to_mm
            length_mm = u_to_mm(float(value))
            self.stabilizer_length_spin.blockSignals(True)
            self.stabilizer_length_spin.setValue(length_mm)
            self.stabilizer_length_spin.blockSignals(False)
            self.on_parameter_changed()
        except Exception:
            pass

    def _on_stabilizer_length_changed(self, value: float):
        """卫星轴长度改变时，更新类型选择"""
        try:
            from core.keycap_presets import u_to_mm
            if abs(value - u_to_mm(2.0)) < 1.0:
                self.stabilizer_type_combo.setCurrentIndex(1)
            elif abs(value - u_to_mm(6.25)) < 1.0:
                self.stabilizer_type_combo.setCurrentIndex(2)
            else:
                self.stabilizer_type_combo.setCurrentIndex(0)
        except Exception:
            self.stabilizer_type_combo.setCurrentIndex(0)
        self.on_parameter_changed()
    
    def _update_params_from_ui(self):
        """从UI更新参数（内部使用，不发信号）"""
        if not self.params.use_u_units:
            self.params.key_width = self.width_spin.value()
            self.params.key_height = self.height_spin.value()
        self.params.key_depth = self.depth_spin.value()
        self.params.wall_thickness = self.wall_spin.value()
        self.params.side_angle = self.side_angle_spin.value()
        self.params.letter = self.letter_edit.text() or "A"
        self.params.text_height = self.text_height_spin.value()
        self.params.text_depth = self.text_depth_spin.value()
        self.params.stem_type = self.stem_combo.currentText()
        self.params.stem_enabled = self.stem_enabled_checkbox.isChecked()
        self.params.stem_height = self.stem_height_spin.value()
        self.params.stem_cylinder_diameter = self.stem_cylinder_spin.value()
        self.params.stem_cross_length = self.stem_cross_length_spin.value()
        self.params.stem_cross_width = self.stem_cross_width_spin.value()
        self.params.height_profile = self.height_profile_combo.currentText()
        self.params.keycap_row = self.row_combo.currentText()

        # 边缘形状参数
        mode_map = {"圆角": "fillet", "45度斜角": "chamfer"}
        self.params.edge_profile_mode = mode_map.get(self.edge_mode_combo.currentText(), "fillet")
        self.params.edge_profile_radius = self.edge_radius_spin.value()
        self.params.edge_profile_outer = self.edge_outer_check.isChecked()
        self.params.edge_profile_inner = self.edge_inner_check.isChecked()
        self.params.edge_profile_left = self.edge_left_check.isChecked()
        self.params.edge_profile_right = self.edge_right_check.isChecked()
        self.params.edge_profile_top = self.edge_top_check.isChecked()
        self.params.edge_profile_bottom = self.edge_bottom_check.isChecked()

        # 卫星轴参数（单键）
        self.params.stabilizer_enabled = self.stabilizer_enabled_checkbox.isChecked()
        self.params.stabilizer_length = self.stabilizer_length_spin.value()

    def on_parameter_changed(self, *args):
        """参数改变时的处理"""
        self._update_params_from_ui()
        # 发出信号
        self.parameters_changed.emit(self.params)
    
    def on_insert_text_clicked(self):
        """插入文字按钮点击"""
        text = self.letter_edit.text() or "A"
        font_size = self.text_height_spin.value()
        self.insert_text_signal.emit(text, font_size)
    
    def get_parameters(self) -> KeycapParameters:
        """获取当前参数"""
        self._update_params_from_ui()
        return self.params
    
    def load_default_parameters(self):
        """从设置中加载默认参数"""
        if not self.settings:
            return
        
        # 加载默认斜角
        default_side_angle = self.settings.get_default_side_angle()
        self.side_angle_spin.setValue(default_side_angle)
        self.params.side_angle = default_side_angle
        
        # 加载默认边缘形状参数
        mode_map = {"fillet": "圆角", "chamfer": "45度斜角"}
        default_mode = self.settings.get_default_edge_profile_mode()
        self.edge_mode_combo.setCurrentText(mode_map.get(default_mode, "圆角"))
        self.edge_radius_spin.setValue(self.settings.get_default_edge_profile_radius())
        self.edge_outer_check.setChecked(self.settings.get_default_edge_profile_outer())
        self.edge_inner_check.setChecked(self.settings.get_default_edge_profile_inner())
        self.edge_left_check.setChecked(self.settings.get_default_edge_profile_left())
        self.edge_right_check.setChecked(self.settings.get_default_edge_profile_right())
        self.edge_top_check.setChecked(self.settings.get_default_edge_profile_top())
        self.edge_bottom_check.setChecked(self.settings.get_default_edge_profile_bottom())

        self.params.edge_profile_mode = default_mode
        self.params.edge_profile_radius = self.edge_radius_spin.value()
        self.params.edge_profile_outer = self.edge_outer_check.isChecked()
        self.params.edge_profile_inner = self.edge_inner_check.isChecked()
        self.params.edge_profile_left = self.edge_left_check.isChecked()
        self.params.edge_profile_right = self.edge_right_check.isChecked()
        self.params.edge_profile_top = self.edge_top_check.isChecked()
        self.params.edge_profile_bottom = self.edge_bottom_check.isChecked()
        
        # 加载默认字体
        default_font_path = self.settings.get_default_font_path()
        if default_font_path:
            # 尝试在字体列表中找到该字体
            for i in range(self.font_combo.count()):
                if self.font_combo.itemData(i) == default_font_path:
                    self.font_combo.setCurrentIndex(i)
                    self.params.font_path = default_font_path
                    break
