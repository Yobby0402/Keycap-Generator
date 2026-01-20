"""
参数输入面板
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QDoubleSpinBox, QComboBox, QPushButton,
                             QGroupBox, QFileDialog, QMessageBox, QCheckBox)
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.params = KeycapParameters()
        self.setup_ui()
        self.load_system_fonts()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
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
        
        # 顶部斜角
        top_angle_layout = QHBoxLayout()
        top_angle_layout.addWidget(QLabel("顶部斜角:"))
        self.top_angle_spin = QDoubleSpinBox()
        self.top_angle_spin.setRange(0.0, 45.0)
        self.top_angle_spin.setValue(0.0)
        self.top_angle_spin.setDecimals(1)
        self.top_angle_spin.setSuffix(" °")
        self.top_angle_spin.valueChanged.connect(self.on_parameter_changed)
        top_angle_layout.addWidget(self.top_angle_spin)
        angle_layout.addLayout(top_angle_layout)
        
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
        self.stem_combo.currentTextChanged.connect(self.on_stem_type_changed)
        type_layout.addWidget(self.stem_combo)
        stem_layout.addLayout(type_layout)
        
        # 连接器深度（所有类型共用）
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
        
        # MX类型参数组
        self.mx_params_widget = QWidget()
        mx_params_layout = QVBoxLayout(self.mx_params_widget)
        mx_params_layout.setContentsMargins(0, 0, 0, 0)
        
        # 圆柱直径（仅MX）
        cylinder_layout = QHBoxLayout()
        cylinder_layout.addWidget(QLabel("圆柱直径:"))
        self.stem_cylinder_spin = QDoubleSpinBox()
        self.stem_cylinder_spin.setRange(3.0, 10.0)
        self.stem_cylinder_spin.setValue(5.4)
        self.stem_cylinder_spin.setDecimals(1)
        self.stem_cylinder_spin.setSuffix(" mm")
        self.stem_cylinder_spin.valueChanged.connect(self.on_parameter_changed)
        cylinder_layout.addWidget(self.stem_cylinder_spin)
        mx_params_layout.addLayout(cylinder_layout)
        
        # 十字尺寸（仅MX）
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
        mx_params_layout.addLayout(cross_layout)
        
        stem_layout.addWidget(self.mx_params_widget)
        
        # Alps类型参数组
        self.alps_params_widget = QWidget()
        alps_params_layout = QVBoxLayout(self.alps_params_widget)
        alps_params_layout.setContentsMargins(0, 0, 0, 0)
        
        # Alps矩形尺寸（仅Alps）
        alps_size_layout = QHBoxLayout()
        alps_size_layout.addWidget(QLabel("矩形尺寸:"))
        self.stem_alps_width_spin = QDoubleSpinBox()
        self.stem_alps_width_spin.setRange(1.0, 5.0)
        self.stem_alps_width_spin.setValue(2.0)
        self.stem_alps_width_spin.setDecimals(1)
        self.stem_alps_width_spin.setSuffix(" mm")
        self.stem_alps_width_spin.valueChanged.connect(self.on_parameter_changed)
        alps_size_layout.addWidget(QLabel("宽度"))
        alps_size_layout.addWidget(self.stem_alps_width_spin)
        
        self.stem_alps_length_spin = QDoubleSpinBox()
        self.stem_alps_length_spin.setRange(2.0, 8.0)
        self.stem_alps_length_spin.setValue(4.0)
        self.stem_alps_length_spin.setDecimals(1)
        self.stem_alps_length_spin.setSuffix(" mm")
        self.stem_alps_length_spin.valueChanged.connect(self.on_parameter_changed)
        alps_size_layout.addWidget(QLabel("长度"))
        alps_size_layout.addWidget(self.stem_alps_length_spin)
        alps_params_layout.addLayout(alps_size_layout)
        
        stem_layout.addWidget(self.alps_params_widget)
        
        # 初始状态：显示MX参数，隐藏Alps参数
        self.mx_params_widget.setVisible(True)
        self.alps_params_widget.setVisible(False)
        
        stem_group.setLayout(stem_layout)
        layout.addWidget(stem_group)
        
        # 按钮
        self.generate_btn = QPushButton("生成模型")
        self.generate_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self.generate_btn)
        
        layout.addStretch()
    
    def load_system_fonts(self):
        """加载系统字体"""
        try:
            fonts = get_system_fonts()
            for font_path in fonts[:100]:  # 限制显示前100个字体
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
    
    def on_stem_type_changed(self, stem_type: str):
        """连接器类型改变时的处理"""
        # 根据类型显示/隐藏相应的参数控件
        if stem_type == "MX":
            self.mx_params_widget.setVisible(True)
            self.alps_params_widget.setVisible(False)
        elif stem_type == "Alps":
            self.mx_params_widget.setVisible(False)
            self.alps_params_widget.setVisible(True)
        
        # 更新参数并发出信号
        self.on_parameter_changed()
    
    def on_parameter_changed(self):
        """参数改变时的处理"""
        # 更新参数对象
        if not self.params.use_u_units:
            self.params.key_width = self.width_spin.value()
            self.params.key_height = self.height_spin.value()
        self.params.key_depth = self.depth_spin.value()
        self.params.wall_thickness = self.wall_spin.value()
        self.params.top_angle = self.top_angle_spin.value()
        self.params.side_angle = self.side_angle_spin.value()
        self.params.letter = self.letter_edit.text() or "A"
        self.params.text_height = self.text_height_spin.value()
        self.params.text_depth = self.text_depth_spin.value()
        self.params.stem_type = self.stem_combo.currentText()
        self.params.stem_enabled = self.stem_enabled_checkbox.isChecked()
        self.params.stem_height = self.stem_height_spin.value()
        
        # MX类型参数
        self.params.stem_cylinder_diameter = self.stem_cylinder_spin.value()
        self.params.stem_cross_length = self.stem_cross_length_spin.value()
        self.params.stem_cross_width = self.stem_cross_width_spin.value()
        
        # Alps类型参数
        self.params.stem_alps_width = self.stem_alps_width_spin.value()
        self.params.stem_alps_length = self.stem_alps_length_spin.value()
        
        self.params.height_profile = self.height_profile_combo.currentText()
        self.params.keycap_row = self.row_combo.currentText()
        
        # 发出信号
        self.parameters_changed.emit(self.params)
    
    def on_insert_text_clicked(self):
        """插入文字按钮点击"""
        text = self.letter_edit.text() or "A"
        font_size = self.text_height_spin.value()
        self.insert_text_signal.emit(text, font_size)
    
    def get_parameters(self) -> KeycapParameters:
        """获取当前参数"""
        self.on_parameter_changed()
        return self.params
