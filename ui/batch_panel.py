"""
批量生成设置面板
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QComboBox,
                             QMessageBox, QSplitter, QRadioButton, QButtonGroup,
                             QDoubleSpinBox, QFormLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.kle_import_dialog import KLEImportDialog
from core.keycap_presets import KEYCAP_HEIGHT_PROFILES, get_keycap_height

class BatchPanel(QWidget):
    """批量生成参数面板"""
    
    # 信号
    kle_data_changed = pyqtSignal(list) # 发送解析后的 KLE 数据列表
    generate_batch_signal = pyqtSignal() # 请求生成
    generate_all_signal = pyqtSignal() # 请求生成所有按键预览
    export_all_signal = pyqtSignal() # 请求导出所有
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_spacing = 2.0  # 行间距 (mm)
        self.col_spacing = 2.0  # 列间距 (mm)
        self.kle_keys = []  # KLE按键列表
        self.row_heights = {}  # {row_y: height_mm} 每行的高度设置
        self.height_profile = "Cherry高度"  # 当前选择的高度类型
        self.use_height_profile = False  # 是否使用高度类型（覆盖单个按键的高度设置）
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. 间距设置（样式映射已移至属性面板显示）
        spacing_group = QGroupBox("模型间距设置")
        spacing_layout = QFormLayout()
        spacing_layout.setSpacing(8)  # 增加间距
        
        # 行间距
        self.row_spacing_spin = QDoubleSpinBox()
        self.row_spacing_spin.setRange(0.0, 20.0)
        self.row_spacing_spin.setValue(self.row_spacing)
        self.row_spacing_spin.setDecimals(1)
        self.row_spacing_spin.setSuffix(" mm")
        self.row_spacing_spin.setMinimumHeight(25)  # 增加控件高度
        def update_row_spacing(v):
            self.row_spacing = v
            print(f"行间距已更新为: {v}mm")
        self.row_spacing_spin.valueChanged.connect(update_row_spacing)
        spacing_layout.addRow("行间距:", self.row_spacing_spin)
        
        # 列间距
        self.col_spacing_spin = QDoubleSpinBox()
        self.col_spacing_spin.setRange(0.0, 20.0)
        self.col_spacing_spin.setValue(self.col_spacing)
        self.col_spacing_spin.setDecimals(1)
        self.col_spacing_spin.setSuffix(" mm")
        self.col_spacing_spin.setMinimumHeight(25)  # 增加控件高度
        def update_col_spacing(v):
            self.col_spacing = v
            print(f"列间距已更新为: {v}mm")
        self.col_spacing_spin.valueChanged.connect(update_col_spacing)
        spacing_layout.addRow("列间距:", self.col_spacing_spin)
        
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)
        
        # 2. 高度类型设置（使用左右布局）
        height_group = QGroupBox("高度类型设置")
        height_main_layout = QHBoxLayout()  # 主布局：左右
        
        # 左侧：控制选项
        left_control_layout = QVBoxLayout()
        
        # 启用高度类型覆盖
        self.use_height_profile_check = QCheckBox("使用高度类型（覆盖单个按键的高度设置）")
        self.use_height_profile_check.setChecked(False)
        self.use_height_profile_check.stateChanged.connect(self.on_use_height_profile_changed)
        left_control_layout.addWidget(self.use_height_profile_check)
        
        # 高度类型选择
        profile_layout = QHBoxLayout()
        profile_label = QLabel("高度类型:")
        profile_label.setMinimumWidth(80)  # 设置标签最小宽度
        profile_layout.addWidget(profile_label)
        self.height_profile_combo = QComboBox()
        self.height_profile_combo.addItems(list(KEYCAP_HEIGHT_PROFILES.keys()))
        self.height_profile_combo.setCurrentText("Cherry高度")
        self.height_profile_combo.currentTextChanged.connect(self.on_height_profile_changed)
        self.height_profile_combo.setMinimumHeight(25)  # 增加控件高度
        profile_layout.addWidget(self.height_profile_combo)
        left_control_layout.addLayout(profile_layout)
        
        left_control_layout.addStretch()
        
        # 右侧：行高度表格
        right_table_layout = QVBoxLayout()
        table_label = QLabel("各行高度设置:")
        table_label.setStyleSheet("font-weight: bold;")
        right_table_layout.addWidget(table_label)
        self.row_height_table = QTableWidget()
        self.row_height_table.setColumnCount(3)
        self.row_height_table.setHorizontalHeaderLabels(["行号", "行标识", "高度 (mm)"])
        self.row_height_table.horizontalHeader().setStretchLastSection(True)
        self.row_height_table.setMinimumHeight(180)
        self.row_height_table.setMaximumHeight(350)
        self.row_height_table.verticalHeader().setDefaultSectionSize(30)  # 增加行高
        right_table_layout.addWidget(self.row_height_table)
        
        # 将左右布局添加到主布局
        left_widget = QWidget()
        left_widget.setLayout(left_control_layout)
        left_widget.setMaximumWidth(250)  # 限制左侧宽度
        height_main_layout.addWidget(left_widget)
        
        right_widget = QWidget()
        right_widget.setLayout(right_table_layout)
        height_main_layout.addWidget(right_widget, stretch=1)  # 右侧占据剩余空间
        
        height_group.setLayout(height_main_layout)
        layout.addWidget(height_group)
        
        # 3. 操作区
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout()
        action_layout.setSpacing(8)  # 增加间距
        
        btn_layout = QVBoxLayout()  # 改为垂直布局，按钮更大更容易点击
        self.gen_btn = QPushButton("生成当前选中 (预览)")
        self.gen_btn.setMinimumHeight(35)  # 增加按钮高度
        self.gen_btn.clicked.connect(self.generate_batch_signal.emit)
        btn_layout.addWidget(self.gen_btn)
        
        self.gen_all_btn = QPushButton("生成所有按键预览")
        self.gen_all_btn.setMinimumHeight(35)  # 增加按钮高度
        self.gen_all_btn.clicked.connect(self.generate_all_signal.emit)
        btn_layout.addWidget(self.gen_all_btn)
        
        self.export_all_btn = QPushButton("导出所有...")
        self.export_all_btn.setMinimumHeight(35)  # 增加按钮高度
        self.export_all_btn.clicked.connect(self.export_all_signal.emit)
        btn_layout.addWidget(self.export_all_btn)
        
        action_layout.addLayout(btn_layout)
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        layout.addStretch()
    
    def set_kle_keys(self, keys):
        """设置KLE按键列表，并更新行高度表格"""
        self.kle_keys = keys
        self.update_row_height_table()
    
    def update_row_height_table(self):
        """更新行高度表格"""
        if not self.kle_keys:
            self.row_height_table.setRowCount(0)
            return
        
        # 按行分组按键
        rows = {}
        for key in self.kle_keys:
            row_y = key.y
            if row_y not in rows:
                rows[row_y] = []
            rows[row_y].append(key)
        
        # 按y坐标排序行
        sorted_rows = sorted(rows.keys())
        
        # 设置表格行数
        self.row_height_table.setRowCount(len(sorted_rows))
        
        # 填充表格
        for idx, row_y in enumerate(sorted_rows):
            # 行号（从1开始）
            row_num_item = QTableWidgetItem(f"第{idx+1}行")
            row_num_item.setFlags(Qt.ItemIsEnabled)  # 只读
            self.row_height_table.setItem(idx, 0, row_num_item)
            
            # 行标识（Y坐标）
            row_id_item = QTableWidgetItem(f"Y={row_y:.2f}")
            row_id_item.setFlags(Qt.ItemIsEnabled)  # 只读
            self.row_height_table.setItem(idx, 1, row_id_item)
            
            # 高度输入（可编辑）
            # 根据当前高度类型和行号计算默认高度
            # 行号映射：第1行=R1，第2行=R2，第3行=R3，第4行=R4，超过4行循环
            row_name = f"R{((idx) % 4) + 1}"
            default_height = get_keycap_height(self.height_profile, row_name)
            
            # 如果已有设置，使用已有设置；否则使用默认值
            if row_y in self.row_heights:
                height_value = self.row_heights[row_y]
            else:
                height_value = default_height
                self.row_heights[row_y] = height_value
            
            height_spin = QDoubleSpinBox()
            height_spin.setRange(1.0, 50.0)
            height_spin.setValue(height_value)
            height_spin.setDecimals(2)
            height_spin.setSuffix(" mm")
            height_spin.setMinimumHeight(28)  # 增加控件高度，方便点击
            height_spin.setMinimumWidth(100)  # 设置最小宽度
            height_spin.valueChanged.connect(lambda v, y=row_y: self.on_row_height_changed(y, v))
            self.row_height_table.setCellWidget(idx, 2, height_spin)
        
        # 调整列宽
        self.row_height_table.resizeColumnsToContents()
    
    def on_use_height_profile_changed(self, state):
        """高度类型覆盖开关改变"""
        self.use_height_profile = (state == Qt.Checked)
        # 更新行高度表格（根据新的高度类型）
        if self.use_height_profile:
            self.update_row_height_table()
    
    def on_height_profile_changed(self, profile_name):
        """高度类型改变"""
        self.height_profile = profile_name
        # 如果启用了高度类型，更新所有行的高度
        if self.use_height_profile:
            # 按行分组按键
            rows = {}
            for key in self.kle_keys:
                row_y = key.y
                if row_y not in rows:
                    rows[row_y] = []
                rows[row_y].append(key)
            
            sorted_rows = sorted(rows.keys())
            
            # 更新每行的高度
            for idx, row_y in enumerate(sorted_rows):
                row_name = f"R{((idx) % 4) + 1}"
                new_height = get_keycap_height(profile_name, row_name)
                self.row_heights[row_y] = new_height
                
                # 更新表格中的值
                height_spin = self.row_height_table.cellWidget(idx, 2)
                if height_spin:
                    height_spin.blockSignals(True)
                    height_spin.setValue(new_height)
                    height_spin.blockSignals(False)
    
    def on_row_height_changed(self, row_y, height):
        """某行高度改变"""
        self.row_heights[row_y] = height
    
    def get_row_height(self, row_y):
        """获取指定行的高度"""
        if self.use_height_profile and row_y in self.row_heights:
            return self.row_heights[row_y]
        return None  # 返回None表示使用单个按键的原有高度设置
    
    def get_height_profile(self):
        """获取当前高度类型"""
        return self.height_profile if self.use_height_profile else None
