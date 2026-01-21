"""
主窗口
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                             QStatusBar, QProgressBar, QDialog, QActionGroup,
                             QTabWidget, QStackedWidget, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from ui.parameter_panel import ParameterPanel
from ui.batch_panel import BatchPanel
from ui.preview_widget import PreviewWidget
from ui.preview_2d_widget import Preview2DWidget
from ui.kle_preview_widget import KLEPreviewWidget
from ui.settings_dialog import SettingsDialog
from core.parameters import KeycapParameters, TextParameters
from core.keycap_modeler import KeycapModeler
from core.settings import Settings
from export.stl_exporter import export_keycap_and_text as export_stl_keycap_text
from export.step_exporter import export_keycap_and_text as export_step_keycap_text
from export.threemf_exporter import export_3mf
import cadquery as cq
import os


class ModelGenerationThread(QThread):
    """模型生成线程（避免UI阻塞）"""
    
    finished = pyqtSignal(object, object)  # (keycap_model, text_model)
    error = pyqtSignal(str)
    
    def __init__(self, params: KeycapParameters):
        super().__init__()
        self.params = params
    
    def run(self):
        """运行模型生成"""
        try:
            modeler = KeycapModeler(self.params)
            keycap_model, text_model = modeler.generate()
            self.finished.emit(keycap_model, text_model)
        except Exception as e:
            self.error.emit(str(e))


class BatchGenerationThread(QThread):
    """批量生成线程（避免UI阻塞）"""
    
    progress = pyqtSignal(int, int)  # (current, total)
    key_generated = pyqtSignal(object, object, float, float, float)  # (keycap_model, text_model, x, y, z)
    finished = pyqtSignal(list, list)  # (keycap_models, text_models)
    error = pyqtSignal(str)
    
    def __init__(self, kle_keys, batch_configs, default_geometry, default_font, row_spacing=2.0, col_spacing=2.0, row_heights=None):
        super().__init__()
        self.kle_keys = kle_keys
        self.batch_configs = batch_configs
        self.default_geometry = default_geometry
        self.default_font = default_font
        self.row_spacing = row_spacing
        self.col_spacing = col_spacing
        self.row_heights = row_heights or {}  # {row_y: height_mm} 行高度映射
    
    def run(self):
        """运行批量生成（应用间距）"""
        try:
            from core.batch_generator import BatchGenerator
            from core.legend_mapping import LegendMapping, LegendStyle
            from core.key_type_analyzer import KeyTypeAnalyzer
            from core.keycap_presets import u_to_mm
            
            keycap_models = []
            text_models = []
            
            # 按照KLE坐标排序（先按y坐标，再按x坐标）
            sorted_keys = sorted(self.kle_keys, key=lambda k: (k.y, k.x))
            
            # 按行分组按键
            rows = {}
            for kle_key in sorted_keys:
                row_y = kle_key.y
                if row_y not in rows:
                    rows[row_y] = []
                rows[row_y].append(kle_key)
            
            # 按y坐标排序行
            sorted_rows = sorted(rows.keys())
            
            # 计算第一行的起始y位置
            first_row_max_height = 0.0
            if sorted_rows:
                first_row_keys = rows[sorted_rows[0]]
                for key in first_row_keys:
                    first_row_max_height = max(first_row_max_height, u_to_mm(key.height))
            
            current_y = first_row_max_height / 2
            max_row_height = 0.0
            
            for row_idx, row_y in enumerate(sorted_rows):
                row_keys = sorted(rows[row_y], key=lambda k: k.x)
                current_x = 0.0  # 每行从x=0开始
                
                for i, kle_key in enumerate(row_keys):
                    self.progress.emit(len(keycap_models) + 1, len(self.kle_keys))
                    
                    # 为每个按键获取对应的配置
                    batch_config = self.batch_configs.get(KeyTypeAnalyzer.get_signature_for_key(kle_key).to_string()) if self.batch_configs else None
                    
                    # 创建生成器
                    if batch_config:
                        global_geometry = batch_config.geometry
                        # 确保卫星轴参数被正确设置
                        if not hasattr(global_geometry, 'stabilizer_enabled'):
                            global_geometry.stabilizer_enabled = getattr(batch_config.geometry, 'stabilizer_enabled', False)
                        if not hasattr(global_geometry, 'stabilizer_length'):
                            global_geometry.stabilizer_length = getattr(batch_config.geometry, 'stabilizer_length', 50.0)
                        legend_mapping = LegendMapping()
                        for pos_idx, style in batch_config.text_styles.items():
                            if style.font_path is None:
                                style.font_path = self.default_font
                            legend_mapping.set_style(pos_idx, style)
                    else:
                        global_geometry = self.default_geometry
                        legend_mapping = LegendMapping.create_default()
                        if self.default_font:
                            for style in legend_mapping.mapping.values():
                                if style.font_path is None:
                                    style.font_path = self.default_font
                    
                    # 应用行高度设置（如果启用）
                    if self.row_heights and row_y in self.row_heights:
                        # 创建几何参数的副本，避免修改原始对象
                        from copy import deepcopy
                        geometry_copy = deepcopy(global_geometry)
                        geometry_copy.key_depth = self.row_heights[row_y]
                        global_geometry = geometry_copy
                        print(f"【行高度】应用行高度: Y={row_y:.2f}, 高度={self.row_heights[row_y]:.2f}mm")
                    
                    generator = BatchGenerator(global_geometry, legend_mapping)
                    generator.set_default_font(self.default_font)
                    
                    # 生成模型
                    keycap_model, text_model = generator.generate_single_key(kle_key)
                    
                    if keycap_model:
                        key_width = u_to_mm(kle_key.width)
                        key_height = u_to_mm(kle_key.height)
                        
                        # 计算按键中心位置（应用间距）
                        key_center_x = current_x + key_width / 2
                        key_center_y = current_y - key_height / 2
                        
                        keycap_models.append((keycap_model, (key_center_x, key_center_y, 0)))
                        if text_model:
                            text_models.append((text_model, (key_center_x, key_center_y, 0)))
                        
                        # 更新下一个按键的x位置
                        current_x += key_width + self.col_spacing
                        max_row_height = max(max_row_height, key_height)
                
                # 换行：更新y位置
                if row_idx < len(sorted_rows) - 1:
                    current_y -= max_row_height + self.row_spacing
                    max_row_height = 0.0
            
            self.finished.emit(keycap_models, text_models)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_keycap_model = None
        self.current_text_model = None
        self.last_generated_text_pos = None # 上次生成时的文字位置 (x, y)
        self.settings = Settings()
        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()
        self.load_settings()
        
        # 自动更新定时器
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(800) # 800ms 防抖
        self.update_timer.timeout.connect(self.generate_model)
        
        # 初始化2D预览内容 (保持与参数一致)
        init_text = self.parameter_panel.params.letter
        init_size = self.parameter_panel.params.text_height
        if init_text:
            self.preview_2d_widget.add_text(init_text, init_size)
        
        # 启动时按照默认参数生成3D预览
        # 使用QTimer延迟执行，确保UI完全初始化后再生成
        QTimer.singleShot(100, self.generate_model)
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("机械键盘按键模型生成器")
        self.setMinimumSize(1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局：使用 TabWidget 直接管理两个模式
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 模式切换标签
        self.mode_tabs = QTabWidget()
        
        # ===== Tab 0: 单键设计（左右布局） =====
        single_key_widget = QWidget()
        single_key_layout = QHBoxLayout(single_key_widget)
        single_key_layout.setSpacing(5)
        single_key_layout.setContentsMargins(5, 5, 5, 5)
        
        # 左侧参数面板（传入settings以便加载默认参数）
        self.parameter_panel = ParameterPanel(settings=self.settings)
        self.parameter_panel.parameters_changed.connect(self.on_parameters_changed)
        self.parameter_panel.generate_btn.clicked.connect(self.generate_model)
        self.parameter_panel.insert_text_signal.connect(self.on_insert_text)
        single_key_layout.addWidget(self.parameter_panel, stretch=1)
        
        # 右侧预览区域
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(5)
        
        # 2D 预览
        self.preview_2d_widget = Preview2DWidget()
        self.preview_2d_widget.text_position_changed.connect(self.on_text_position_changed)
        self.preview_2d_widget.drag_finished.connect(self.check_auto_update)
        self.preview_2d_widget.content_changed.connect(self.check_auto_update)
        # 从设置加载对齐配置
        self.preview_2d_widget.snap_enabled = self.settings.get_snap_enabled()
        self.preview_2d_widget.snap_grid_size = self.settings.get_snap_grid_size()
        preview_layout.addWidget(self.preview_2d_widget, stretch=1)
        
        # 3D 预览
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget, stretch=2)
        
        preview_container = QWidget()
        preview_container.setLayout(preview_layout)
        single_key_layout.addWidget(preview_container, stretch=2)
        
        self.mode_tabs.addTab(single_key_widget, "单键设计")
        
        # ===== Tab 1: 批量布局（上下布局） =====
        batch_widget = QWidget()
        batch_layout = QVBoxLayout(batch_widget)
        batch_layout.setSpacing(5)
        batch_layout.setContentsMargins(5, 5, 5, 5)
        
        # 上方区域：左右布局（预览 + 属性面板）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(5)
        
        # 左侧：预览区域（2D + 3D）
        batch_preview_layout = QVBoxLayout()
        batch_preview_layout.setSpacing(5)
        
        # KLE 2D 预览
        self.kle_preview_widget = KLEPreviewWidget()
        self.kle_preview_widget.key_selected.connect(self.on_kle_key_selected)
        # 连接间距更新信号
        self.batch_panel = None  # 稍后在setup_ui中设置
        batch_preview_layout.addWidget(self.kle_preview_widget, stretch=1)
        
        # 3D 预览（批量模式也显示）
        self.batch_preview_widget = PreviewWidget()
        batch_preview_layout.addWidget(self.batch_preview_widget, stretch=1)
        
        batch_preview_container = QWidget()
        batch_preview_container.setLayout(batch_preview_layout)
        top_layout.addWidget(batch_preview_container, stretch=3)
        
        # 右侧：属性面板（集成编辑功能）
        from ui.key_property_panel import KeyPropertyPanel
        self.key_property_panel = KeyPropertyPanel()
        self.key_property_panel.data_updated.connect(self.on_kle_key_updated_and_preview)
        top_layout.addWidget(self.key_property_panel, stretch=1)
        
        batch_layout.addLayout(top_layout, stretch=2)
        
        # 下方参数面板
        self.batch_panel = BatchPanel()
        self.batch_panel.kle_data_changed.connect(self.on_kle_data_changed)
        self.batch_panel.generate_batch_signal.connect(self.on_generate_batch)
        self.batch_panel.generate_all_signal.connect(self.on_generate_all_keys)
        self.batch_panel.export_all_signal.connect(self.on_export_all)
        
        # 连接间距更新到2D预览
        def update_2d_spacing():
            row_spacing = getattr(self.batch_panel, 'row_spacing', 2.0)
            col_spacing = getattr(self.batch_panel, 'col_spacing', 2.0)
            self.kle_preview_widget.set_spacing(row_spacing, col_spacing)
        
        # 监听间距变化（直接连接spinbox）
        if hasattr(self.batch_panel, 'row_spacing_spin'):
            self.batch_panel.row_spacing_spin.valueChanged.connect(update_2d_spacing)
        if hasattr(self.batch_panel, 'col_spacing_spin'):
            self.batch_panel.col_spacing_spin.valueChanged.connect(update_2d_spacing)
        
        batch_layout.addWidget(self.batch_panel, stretch=1)
        
        self.mode_tabs.addTab(batch_widget, "批量布局")
        
        # ===== Tab 2: 批量编辑 =====
        from ui.batch_edit_tab import BatchEditTab
        self.batch_edit_tab = BatchEditTab()
        self.batch_edit_tab.config_applied.connect(self.on_batch_config_applied)
        self.mode_tabs.addTab(self.batch_edit_tab, "批量编辑")
        
        main_layout.addWidget(self.mode_tabs)
        
    def on_mode_changed(self, index):
        """模式切换处理（单键/批量）"""
        # TabWidget 会自动处理切换，这里可以添加额外的逻辑
        pass
        
    def import_kle_layout(self):
        """从菜单栏导入KLE布局"""
        from ui.kle_import_dialog import KLEImportDialog
        dialog = KLEImportDialog(self)
        dialog.data_parsed.connect(self.on_kle_data_changed)
        dialog.exec_()
    
    def on_kle_data_changed(self, keys):
        """KLE 数据更新"""
        self.kle_preview_widget.set_data(keys)
        
        # 设置初始间距（从batch_panel获取，确保与UI一致）
        row_spacing = getattr(self.batch_panel, 'row_spacing', 2.0)
        col_spacing = getattr(self.batch_panel, 'col_spacing', 2.0)
        self.kle_preview_widget.set_spacing(row_spacing, col_spacing)
        
        # 更新批量编辑界面
        if hasattr(self, 'batch_edit_tab'):
            # 获取默认几何参数和字体
            single_params = self.parameter_panel.get_parameters()
            self.batch_edit_tab.load_kle_keys(
                keys=keys,
                default_geometry=single_params.geometry,
                default_font_path=single_params.font_path
            )
            print(f"【KLE数据更新】已加载 {len(keys)} 个按键")
            print(f"  - 批量编辑配置数量: {len(self.batch_edit_tab.configs)}")
            print(f"  - 配置类型列表: {list(self.batch_edit_tab.configs.keys())}")
        
        # 更新批量面板的按键列表（用于高度类型设置）
        if hasattr(self, 'batch_panel'):
            self.batch_panel.set_kle_keys(keys)
    
    def on_batch_config_applied(self, configs: dict):
        """
        批量编辑配置已应用
        
        参数:
            configs: {类型标识: BatchEditConfig}
        """
        # 统计总按键数
        total_keys = 0
        if hasattr(self, 'batch_edit_tab') and hasattr(self.batch_edit_tab, 'type_map'):
            for type_id in configs.keys():
                if type_id in self.batch_edit_tab.type_map:
                    total_keys += len(self.batch_edit_tab.type_map[type_id])
        
        print(f"批量编辑配置已应用: {len(configs)} 个类型，共 {total_keys} 个按键")
        
        # 刷新批量布局界面的2D预览（虽然2D预览主要显示KLE原始数据，但刷新可以确保一致性）
        if hasattr(self, 'kle_preview_widget'):
            self.kle_preview_widget.update()
        
        # 如果当前有选中的按键，更新其3D预览
        if hasattr(self.kle_preview_widget, 'selected_index'):
            selected_index = self.kle_preview_widget.selected_index
            if selected_index >= 0:
                self._preview_single_key(selected_index)
        
        self.status_bar.showMessage(f"批量编辑配置已应用到 {len(configs)} 个类型，共 {total_keys} 个按键")
        
    def on_generate_batch(self):
        """批量生成请求 - 生成当前选中的按键"""
        if not hasattr(self.kle_preview_widget, 'keys') or not self.kle_preview_widget.keys:
            QMessageBox.warning(self, "警告", "请先导入 KLE 布局数据")
            return
        
        selected_index = self.kle_preview_widget.selected_index
        if selected_index < 0 or selected_index >= len(self.kle_preview_widget.keys):
            QMessageBox.warning(self, "警告", "请先选择一个按键（单击预览中的按键）")
            return
        
        # 直接使用_preview_single_key方法（它已经支持批量编辑配置）
        self._preview_single_key(selected_index)
        self.status_bar.showMessage(f"按键 #{selected_index + 1} 生成完成")
    
    def on_generate_all_keys(self):
        """生成所有按键的3D预览（使用后台线程）"""
        if not hasattr(self.kle_preview_widget, 'keys') or not self.kle_preview_widget.keys:
            QMessageBox.warning(self, "警告", "请先导入 KLE 布局数据")
            return
        
        kle_keys = self.kle_preview_widget.keys
        if not kle_keys:
            QMessageBox.warning(self, "警告", "没有可生成的按键")
            return
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(kle_keys))
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("正在生成所有按键的3D预览...")
        
        # 获取批量编辑配置
        batch_configs = {}
        if hasattr(self, 'batch_edit_tab'):
            batch_configs = self.batch_edit_tab.get_configs()
        
        # 获取默认参数
        single_params = self.parameter_panel.get_parameters()
        default_geometry = single_params.geometry
        default_font = single_params.font_path
        
        # 如果没有设置字体，使用Times New Roman作为默认字体
        if not default_font:
            from utils.font_utils import find_times_new_roman
            default_font = find_times_new_roman()
            if default_font:
                print(f"使用默认字体 Times New Roman: {default_font}")
        
        # 获取间距设置（用于预览）
        row_spacing = getattr(self.batch_panel, 'row_spacing', 2.0)
        col_spacing = getattr(self.batch_panel, 'col_spacing', 2.0)
        
        print(f"【生成所有按键预览】间距设置: 行间距={row_spacing}mm, 列间距={col_spacing}mm")
        
        # 获取行高度设置（从batch_panel）
        row_heights = {}
        if hasattr(self.batch_panel, 'use_height_profile') and self.batch_panel.use_height_profile:
            row_heights = self.batch_panel.row_heights.copy()
            print(f"【生成所有按键预览】使用行高度设置: {len(row_heights)} 行")
        
        # 创建后台生成线程（传入间距参数和行高度）
        self.batch_gen_thread = BatchGenerationThread(
            kle_keys, batch_configs, default_geometry, default_font,
            row_spacing=row_spacing, col_spacing=col_spacing, row_heights=row_heights
        )
        self.batch_gen_thread.progress.connect(self.on_batch_progress)
        self.batch_gen_thread.finished.connect(self.on_batch_finished)
        self.batch_gen_thread.error.connect(self.on_batch_error)
        self.batch_gen_thread.start()
    
    def on_batch_progress(self, current, total):
        """批量生成进度更新"""
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"正在生成按键 {current}/{total}...")
    
    def on_batch_finished(self, keycap_models, text_models):
        """批量生成完成"""
        self.progress_bar.setVisible(False)
        if keycap_models:
            self.batch_preview_widget.update_all_models(keycap_models, text_models)
            self.status_bar.showMessage(f"已生成 {len(keycap_models)} 个按键的3D预览")
        else:
            QMessageBox.warning(self, "生成失败", "无法生成任何按键模型")
    
    def on_batch_error(self, error_msg):
        """批量生成错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "生成错误", f"生成过程中出错:\n{error_msg}")
        
    def on_kle_key_selected(self, index):
        """KLE 按键选中 - 单击时更新属性面板（集成编辑功能）"""
        if index < 0 or not hasattr(self.kle_preview_widget, 'keys') or index >= len(self.kle_preview_widget.keys):
            return
        
        key = self.kle_preview_widget.keys[index]
        
        # 查找对应的批量编辑配置
        batch_config = None
        if hasattr(self, 'batch_edit_tab') and hasattr(self.batch_edit_tab, 'configs'):
            from core.key_type_analyzer import KeyTypeAnalyzer
            key_type = KeyTypeAnalyzer.get_signature_for_key(key)
            type_id = key_type.to_string()
            print(f"【按键选中】索引: {index}, 类型ID: {type_id}")
            print(f"  - 可用配置类型: {list(self.batch_edit_tab.configs.keys())}")
            if type_id in self.batch_edit_tab.configs:
                batch_config = self.batch_edit_tab.configs[type_id]
                print(f"  - 找到批量编辑配置: {type_id}")
            else:
                print(f"  - 未找到批量编辑配置，使用默认配置")
        else:
            print(f"  - batch_edit_tab 或 configs 不存在")
        
        # 更新属性面板（包含编辑功能和批量编辑配置）
        self.key_property_panel.update_key(key, index, batch_config)
    
    def on_kle_key_updated_and_preview(self, key_index: int, updated_key):
        """KLE 按键数据更新并预览3D模型"""
        # 更新预览
        if key_index < len(self.kle_preview_widget.keys):
            self.kle_preview_widget.keys[key_index] = updated_key
            self.kle_preview_widget.update()
        
        # 自动生成并预览3D模型
        self._preview_single_key(key_index)
    
    def _preview_single_key(self, key_index: int):
        """预览单个按键的3D模型"""
        if key_index < 0 or not hasattr(self.kle_preview_widget, 'keys') or key_index >= len(self.kle_preview_widget.keys):
            return
        
        from core.batch_generator import BatchGenerator
        from core.legend_mapping import LegendMapping
        
        # 获取选中的按键
        kle_key = self.kle_preview_widget.keys[key_index]
        
        # 尝试从批量编辑配置中获取配置
        batch_config = None
        if hasattr(self, 'batch_edit_tab'):
            batch_config = self.batch_edit_tab.get_config_for_key(kle_key)
        
        # 如果找到批量编辑配置，使用它；否则使用默认配置
        if batch_config:
            # 使用批量编辑的配置
            # 确保几何参数包含卫星轴设置
            global_geometry = batch_config.geometry
            # 确保卫星轴参数被正确设置
            if not hasattr(global_geometry, 'stabilizer_enabled'):
                global_geometry.stabilizer_enabled = getattr(batch_config.geometry, 'stabilizer_enabled', False)
            if not hasattr(global_geometry, 'stabilizer_length'):
                global_geometry.stabilizer_length = getattr(batch_config.geometry, 'stabilizer_length', 50.0)
            
            # 创建自定义样式映射（基于批量编辑配置）
            from core.legend_mapping import LegendMapping, LegendStyle
            legend_mapping = LegendMapping()
            for pos_idx, style in batch_config.text_styles.items():
                legend_mapping.set_style(pos_idx, style)
            
            # 设置默认字体（如果配置中没有指定）
            single_params = self.parameter_panel.get_parameters()
            if single_params.font_path:
                for pos_idx in batch_config.key_type.label_positions:
                    style = batch_config.get_style_for_position(pos_idx, single_params.font_path)
                    if style.font_path is None:
                        style.font_path = single_params.font_path
                    legend_mapping.set_style(pos_idx, style)
            
            print(f"  - 使用批量编辑配置: {batch_config.key_type.to_string()}")
            print(f"  - 卫星轴启用: {global_geometry.stabilizer_enabled}")
            print(f"  - 卫星轴长度: {global_geometry.stabilizer_length}mm")
        else:
            # 使用默认配置
            single_params = self.parameter_panel.get_parameters()
            global_geometry = single_params.geometry
            
            # 创建默认样式映射
            legend_mapping = LegendMapping.create_default()
            # 为所有样式设置字体路径
            if single_params.font_path:
                for style in legend_mapping.mapping.values():
                    if style.font_path is None:
                        style.font_path = single_params.font_path
        
        # 创建生成器
        generator = BatchGenerator(global_geometry, legend_mapping)
        font_path = single_params.font_path if single_params.font_path else None
        if not font_path:
            from utils.font_utils import find_times_new_roman
            font_path = find_times_new_roman()
        generator.set_default_font(font_path)
        
        # 调试信息
        print(f"生成按键 #{key_index + 1}:")
        if batch_config:
            print(f"  - 使用批量编辑配置: {batch_config.key_type.to_string()}")
        else:
            print(f"  - 使用默认配置")
        print(f"  - 字体路径: {single_params.font_path}")
        print(f"  - 按键标签数量: {len(kle_key.labels)}")
        print(f"  - 非空标签: {[i for i, l in enumerate(kle_key.labels) if l and l.strip()]}")
        print(f"  - 卫星轴启用: {global_geometry.stabilizer_enabled if hasattr(global_geometry, 'stabilizer_enabled') else False}")
        print(f"  - 卫星轴长度: {global_geometry.stabilizer_length if hasattr(global_geometry, 'stabilizer_length') else 50.0}mm")
        
        keycap_model, text_model = generator.generate_single_key(kle_key)
        
        if keycap_model:
            # 更新批量模式的 3D 预览
            self.batch_preview_widget.update_model(keycap_model, text_model)
            self.status_bar.showMessage(f"按键 #{key_index + 1} 预览已更新")
        else:
            self.status_bar.showMessage(f"按键 #{key_index + 1} 生成失败")
    
    def on_export_all(self):
        """批量导出所有按键"""
        if not hasattr(self.kle_preview_widget, 'keys') or not self.kle_preview_widget.keys:
            QMessageBox.warning(self, "警告", "请先导入 KLE 布局数据")
            return
        
        from ui.batch_export_dialog import BatchExportDialog
        dialog = BatchExportDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        
        export_mode = dialog.get_export_mode()
        
        # 选择导出目录
        if export_mode == "separate":
            export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
            if not export_dir:
                return
        else:
            # 合并导出，选择文件路径
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "导出合并文件",
                "",
                "STL文件 (*.stl);;STEP文件 (*.step *.stp);;3MF文件 (*.3mf);;所有文件 (*.*)"
            )
            if not file_path:
                return
            
            # 如果用户没有输入扩展名，根据选择的过滤器添加
            if selected_filter:
                if "STL" in selected_filter and not file_path.lower().endswith('.stl'):
                    file_path += '.stl'
                elif "STEP" in selected_filter and not file_path.lower().endswith(('.step', '.stp')):
                    file_path += '.step'
                elif "3MF" in selected_filter and not file_path.lower().endswith('.3mf'):
                    file_path += '.3mf'
            
            export_dir = None
        
        # 执行批量导出
        self._execute_batch_export(export_mode, export_dir if export_mode == "separate" else file_path)
    
    def _execute_batch_export(self, mode: str, path: str):
        """执行批量导出"""
        from core.batch_generator import BatchGenerator
        from core.legend_mapping import LegendMapping, LegendStyle
        from core.parameters import KeycapGeometry
        from export.stl_exporter import export_stl, export_keycap_and_text
        from export.step_exporter import export_step
        from export.threemf_exporter import export_3mf
        from core.key_type_analyzer import KeyTypeAnalyzer
        import cadquery as cq
        import os
        
        # 获取批量编辑配置（如果存在）
        batch_configs = {}
        if hasattr(self, 'batch_edit_tab'):
            batch_configs = self.batch_edit_tab.get_configs()
        
        # 获取默认参数
        single_params = self.parameter_panel.get_parameters()
        default_geometry = single_params.geometry
        default_font = single_params.font_path
        
        # 如果没有设置字体，使用Times New Roman作为默认字体
        if not default_font:
            from utils.font_utils import find_times_new_roman
            default_font = find_times_new_roman()
            if default_font:
                print(f"使用默认字体 Times New Roman: {default_font}")
        
        kle_keys = self.kle_preview_widget.keys
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(kle_keys))
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("正在批量生成...")
        
        if mode == "separate":
            # 分离导出
            success_count = 0
            for i, kle_key in enumerate(kle_keys):
                self.progress_bar.setValue(i + 1)
                self.status_bar.showMessage(f"正在生成按键 {i+1}/{len(kle_keys)}...")
                
                # 为每个按键获取对应的配置
                batch_config = batch_configs.get(KeyTypeAnalyzer.get_signature_for_key(kle_key).to_string()) if batch_configs else None
                
                # 获取行高度设置（从batch_panel）
                row_heights = {}
                if hasattr(self.batch_panel, 'use_height_profile') and self.batch_panel.use_height_profile:
                    row_heights = self.batch_panel.row_heights.copy()
                
                # 创建生成器（使用批量编辑配置或默认配置）
                if batch_config:
                    global_geometry = batch_config.geometry
                    
                    # 应用行高度设置（如果启用）
                    if row_heights and kle_key.y in row_heights:
                        from copy import deepcopy
                        geometry_copy = deepcopy(global_geometry)
                        geometry_copy.key_depth = row_heights[kle_key.y]
                        global_geometry = geometry_copy
                    # 确保卫星轴参数被正确设置
                    if not hasattr(global_geometry, 'stabilizer_enabled'):
                        global_geometry.stabilizer_enabled = getattr(batch_config.geometry, 'stabilizer_enabled', False)
                    if not hasattr(global_geometry, 'stabilizer_length'):
                        global_geometry.stabilizer_length = getattr(batch_config.geometry, 'stabilizer_length', 50.0)
                    legend_mapping = LegendMapping()
                    for pos_idx, style in batch_config.text_styles.items():
                        # 确保字体路径已设置
                        if style.font_path is None:
                            style.font_path = default_font
                        legend_mapping.set_style(pos_idx, style)
                else:
                    global_geometry = default_geometry
                    
                    # 应用行高度设置（如果启用）
                    if row_heights and kle_key.y in row_heights:
                        from copy import deepcopy
                        geometry_copy = deepcopy(global_geometry)
                        geometry_copy.key_depth = row_heights[kle_key.y]
                        global_geometry = geometry_copy
                    
                    legend_mapping = LegendMapping.create_default()
                    if default_font:
                        for style in legend_mapping.mapping.values():
                            if style.font_path is None:
                                style.font_path = default_font
                
                generator = BatchGenerator(global_geometry, legend_mapping)
                generator.set_default_font(default_font)
                
                keycap_model, text_model = generator.generate_single_key(kle_key)
                
                if keycap_model:
                    # 生成文件名（基于位置和字符）
                    main_label = kle_key.labels[9] if len(kle_key.labels) > 9 and kle_key.labels[9] else kle_key.labels[0] if kle_key.labels else "Key"
                    safe_label = "".join(c for c in main_label if c.isalnum() or c in (' ', '-', '_'))[:10]
                    filename = f"Key_R{kle_key.row}_{i+1:02d}_{safe_label}"
                    base_path = os.path.join(path, filename)
                    
                    k_success, t_success = export_keycap_and_text(keycap_model, text_model, base_path)
                    if k_success:
                        success_count += 1
            
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage(f"导出完成：成功 {success_count}/{len(kle_keys)} 个按键")
            QMessageBox.information(self, "导出完成", f"已导出 {success_count} 个按键到:\n{path}")
        else:
            # 合并导出（摆盘）
            # 获取间距设置（直接从控件获取，确保是最新值）
            row_spacing = getattr(self.batch_panel, 'row_spacing', 2.0)
            col_spacing = getattr(self.batch_panel, 'col_spacing', 2.0)
            
            # 调试：检查间距值
            print("=" * 60)
            print(f"【间距设置检查】")
            print(f"  row_spacing 属性值: {getattr(self.batch_panel, 'row_spacing', 'NOT FOUND')}")
            print(f"  col_spacing 属性值: {getattr(self.batch_panel, 'col_spacing', 'NOT FOUND')}")
            print(f"  最终使用值: 行间距={row_spacing}mm, 列间距={col_spacing}mm")
            print("=" * 60)
            
            from core.keycap_presets import u_to_mm
            
            # 按照KLE坐标排序（先按y坐标，再按x坐标）
            # 这样可以确保按键按照正确的行列顺序排列
            sorted_keys = sorted(kle_keys, key=lambda k: (k.y, k.x))
            
            # 收集所有模型并计算位置（使用间距重新计算）
            all_keycaps = []
            all_texts = []
            
            # 按行分组按键
            rows = {}
            for kle_key in sorted_keys:
                row_y = kle_key.y
                if row_y not in rows:
                    rows[row_y] = []
                rows[row_y].append(kle_key)
            
            # 按y坐标排序行
            sorted_rows = sorted(rows.keys())
            
            # 计算第一行的起始y位置（所有按键中最高的）
            first_row_max_height = 0.0
            if sorted_rows:
                first_row_keys = rows[sorted_rows[0]]
                for key in first_row_keys:
                    first_row_max_height = max(first_row_max_height, u_to_mm(key.height))
            
            current_y = first_row_max_height / 2  # 当前行的y位置（从顶部开始，考虑第一行高度）
            max_row_height = 0.0
            
            for row_idx, row_y in enumerate(sorted_rows):
                row_keys = sorted(rows[row_y], key=lambda k: k.x)  # 行内按键按x排序
                current_x = 0.0  # 每行从x=0开始
                
                for i, kle_key in enumerate(row_keys):
                    self.progress_bar.setValue(len(all_keycaps) + 1)
                    self.status_bar.showMessage(f"正在生成按键 {len(all_keycaps) + 1}/{len(kle_keys)}...")
                    
                    # 为每个按键获取对应的配置
                    batch_config = batch_configs.get(KeyTypeAnalyzer.get_signature_for_key(kle_key).to_string()) if batch_configs else None
                    
                    # 获取行高度设置（从batch_panel）
                    row_heights = {}
                    if hasattr(self.batch_panel, 'use_height_profile') and self.batch_panel.use_height_profile:
                        row_heights = self.batch_panel.row_heights.copy()
                    
                    # 创建生成器（使用批量编辑配置或默认配置）
                    if batch_config:
                        global_geometry = batch_config.geometry
                        
                        # 应用行高度设置（如果启用）
                        if row_heights and kle_key.y in row_heights:
                            from copy import deepcopy
                            geometry_copy = deepcopy(global_geometry)
                            geometry_copy.key_depth = row_heights[kle_key.y]
                            global_geometry = geometry_copy
                        # 确保卫星轴参数被正确设置
                        if not hasattr(global_geometry, 'stabilizer_enabled'):
                            global_geometry.stabilizer_enabled = getattr(batch_config.geometry, 'stabilizer_enabled', False)
                        if not hasattr(global_geometry, 'stabilizer_length'):
                            global_geometry.stabilizer_length = getattr(batch_config.geometry, 'stabilizer_length', 50.0)
                        legend_mapping = LegendMapping()
                        for pos_idx, style in batch_config.text_styles.items():
                            # 确保字体路径已设置
                            if style.font_path is None:
                                style.font_path = default_font
                            legend_mapping.set_style(pos_idx, style)
                    else:
                        global_geometry = default_geometry
                        
                        # 应用行高度设置（如果启用）
                        if row_heights and kle_key.y in row_heights:
                            from copy import deepcopy
                            geometry_copy = deepcopy(global_geometry)
                            geometry_copy.key_depth = row_heights[kle_key.y]
                            global_geometry = geometry_copy
                        
                        legend_mapping = LegendMapping.create_default()
                        if default_font:
                            for style in legend_mapping.mapping.values():
                                if style.font_path is None:
                                    style.font_path = default_font
                    
                    generator = BatchGenerator(global_geometry, legend_mapping)
                    generator.set_default_font(default_font)
                    
                    keycap_model, text_model = generator.generate_single_key(kle_key)
                    
                    if keycap_model:
                        key_width = u_to_mm(kle_key.width)
                        key_height = u_to_mm(kle_key.height)
                        
                        # 计算按键中心位置（基于间距重新计算）
                        key_center_x = current_x + key_width / 2
                        key_center_y = current_y - key_height / 2  # Y轴向下
                        
                        # 调试输出：显示每个按键的位置和间距
                        if len(all_keycaps) < 5:  # 输出前5个按键的详细信息
                            print(f"【按键 {len(all_keycaps) + 1}】")
                            print(f"  KLE坐标: x={kle_key.x:.2f}u, y={kle_key.y:.2f}u")
                            print(f"  按键尺寸: {key_width:.2f}mm x {key_height:.2f}mm")
                            print(f"  计算位置: center=({key_center_x:.2f}, {key_center_y:.2f})")
                            print(f"  current_x={current_x:.2f}, col_spacing={col_spacing:.2f}mm")
                        
                        # 移动到摆盘位置
                        keycap_pos = keycap_model.translate((key_center_x, key_center_y, 0))
                        if text_model:
                            text_pos = text_model.translate((key_center_x, key_center_y, 0))
                        else:
                            text_pos = None
                        
                        all_keycaps.append(keycap_pos)
                        if text_pos:
                            all_texts.append(text_pos)
                        
                        # 更新下一个按键的x位置（当前按键右侧 + 间距）
                        # 注意：current_x是下一个按键的左侧位置
                        old_current_x = current_x
                        spacing_added = key_width + col_spacing
                        current_x += spacing_added
                        max_row_height = max(max_row_height, key_height)
                        
                        # 调试输出：显示更新后的current_x
                        if len(all_keycaps) < 5:  # 输出前5个按键的详细信息
                            print(f"  位置更新: current_x {old_current_x:.2f} -> {current_x:.2f} "
                                  f"(增加 {key_width:.2f} + {col_spacing:.2f} = {spacing_added:.2f}mm)")
                            print()
                
                # 换行：更新y位置
                if row_idx < len(sorted_rows) - 1:  # 不是最后一行
                    old_current_y = current_y
                    current_y -= max_row_height + row_spacing
                    print(f"  换行 {row_idx}->{row_idx+1}: current_y从 {old_current_y:.2f} 更新到 {current_y:.2f} "
                          f"(减少 {max_row_height:.2f} + {row_spacing:.2f} = {max_row_height + row_spacing:.2f})")
                    max_row_height = 0.0
            
            # 合并所有模型
            if all_keycaps:
                merged_keycap = all_keycaps[0]
                for k in all_keycaps[1:]:
                    merged_keycap = merged_keycap.union(k)
                
                merged_text = None
                if all_texts:
                    merged_text = all_texts[0]
                    for t in all_texts[1:]:
                        if t:
                            merged_text = merged_text.union(t)
                
                # 导出
                file_ext = os.path.splitext(path)[1].lower()
                if file_ext == '.stl':
                    # STL 需要分开导出
                    base_path = os.path.splitext(path)[0]
                    k_success, t_success = export_keycap_and_text(merged_keycap, merged_text, base_path)
                    if k_success:
                        QMessageBox.information(self, "导出成功", f"已导出合并文件到:\n{base_path}_keycap.stl\n{base_path}_text.stl")
                elif file_ext in ['.step', '.stp']:
                    from export.step_exporter import export_keycap_and_text as export_step_keycap_text
                    base_path = os.path.splitext(path)[0]
                    k_success, t_success = export_step_keycap_text(merged_keycap, merged_text, base_path)
                    if k_success:
                        QMessageBox.information(self, "导出成功", f"已导出合并文件到:\n{base_path}_keycap.step\n{base_path}_text.step")
                elif file_ext == '.3mf':
                    success = export_3mf(merged_keycap, merged_text, path)
                    if success:
                        QMessageBox.information(self, "导出成功", f"已导出合并文件到:\n{path}")
                else:
                    QMessageBox.warning(self, "错误", f"不支持的文件格式: {file_ext}")
            
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage("批量导出完成")
    
    def export_single_key_config(self):
        """导出单个按键配置"""
        from core.keycap_config import KeycapConfig
        from core.batch_generator import BatchGenerator
        from core.legend_mapping import LegendMapping, LegendStyle, _calculate_base_position
        from core.parameters import KeycapDesign, TextParameters
        from core.key_type_analyzer import KeyTypeAnalyzer
        from core.keycap_presets import u_to_mm
        
        # 确定要导出的按键
        key = None
        design = None
        
        # 优先从批量布局界面获取选中的按键
        if hasattr(self, 'kle_preview_widget') and hasattr(self.kle_preview_widget, 'selected_index'):
            selected_index = self.kle_preview_widget.selected_index
            if selected_index >= 0 and selected_index < len(self.kle_preview_widget.keys):
                key = self.kle_preview_widget.keys[selected_index]
                
                # 获取对应的配置（批量编辑或默认）
                batch_config = None
                if hasattr(self, 'batch_edit_tab'):
                    batch_config = self.batch_edit_tab.get_config_for_key(key)
                
                # 创建生成器并转换为设计
                single_params = self.parameter_panel.get_parameters()
                
                if batch_config:
                    # 使用批量编辑配置
                    global_geometry = batch_config.geometry
                    legend_mapping = LegendMapping()
                    for pos_idx, style in batch_config.text_styles.items():
                        legend_mapping.set_style(pos_idx, style)
                    if single_params.font_path:
                        for pos_idx in batch_config.key_type.label_positions:
                            style = batch_config.get_style_for_position(pos_idx, single_params.font_path)
                            if style.font_path is None:
                                style.font_path = single_params.font_path
                            legend_mapping.set_style(pos_idx, style)
                else:
                    # 使用默认配置
                    global_geometry = single_params.geometry
                    legend_mapping = LegendMapping.create_default()
                    if single_params.font_path:
                        for style in legend_mapping.mapping.values():
                            if style.font_path is None:
                                style.font_path = single_params.font_path
                
                generator = BatchGenerator(global_geometry, legend_mapping)
                generator.set_default_font(single_params.font_path)
                design = generator.convert_kle_key_to_design(key)
        
        # 如果批量布局没有选中，尝试从批量编辑界面获取
        if key is None and hasattr(self, 'batch_edit_tab'):
            current_type_id = self.batch_edit_tab.current_type_id
            if current_type_id and current_type_id in self.batch_edit_tab.configs:
                batch_config = self.batch_edit_tab.configs[current_type_id]
                # 从该类型中取第一个按键作为示例
                if current_type_id in self.batch_edit_tab.type_map:
                    indices = self.batch_edit_tab.type_map[current_type_id]
                    if indices and indices[0] < len(self.batch_edit_tab.kle_keys):
                        key = self.batch_edit_tab.kle_keys[indices[0]]
                        # 创建设计（使用批量编辑配置）
                        geometry = batch_config.geometry
                        geometry.key_width = u_to_mm(batch_config.key_type.width)
                        geometry.key_height = u_to_mm(batch_config.key_type.height)
                        
                        text_items = []
                        key_width_mm = geometry.key_width
                        key_height_mm = geometry.key_height
                        single_params = self.parameter_panel.get_parameters()
                        
                        for pos_idx in batch_config.key_type.label_positions:
                            style = batch_config.get_style_for_position(pos_idx, single_params.font_path)
                            base_x, base_y = _calculate_base_position(pos_idx, key_width_mm, key_height_mm)
                            text_param = TextParameters(
                                text="X",  # 使用X作为占位符
                                font_path=style.font_path,
                                size=style.size,
                                depth=style.depth,
                                offset_x=base_x + style.offset_x,
                                offset_y=base_y + style.offset_y
                            )
                            text_items.append(text_param)
                        
                        design = KeycapDesign(geometry=geometry, text_items=text_items)
        
        if key is None or design is None:
            QMessageBox.warning(self, "警告", "请先在批量布局界面选择一个按键，或在批量编辑界面选择一个按键类型")
            return
        
        # 创建配置
        config = KeycapConfig.from_kle_key(key, design)
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出单个按键配置",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        # 确保文件扩展名
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        # 保存配置
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(config.to_json(indent=2))
            QMessageBox.information(self, "导出成功", f"按键配置已导出到:\n{file_path}")
            self.status_bar.showMessage(f"按键配置已导出: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"无法导出配置:\n{str(e)}")
            print(f"导出配置失败: {e}")
            import traceback
            traceback.print_exc()
    
    def export_all_key_configs(self):
        """导出整套按键配置"""
        from core.keycap_config import KeycapConfig, KeycapConfigSet
        from core.batch_generator import BatchGenerator
        from core.legend_mapping import LegendMapping, LegendStyle, _calculate_base_position
        from core.parameters import KeycapDesign, TextParameters
        from core.key_type_analyzer import KeyTypeAnalyzer
        from core.keycap_presets import u_to_mm
        
        # 检查是否有批量编辑配置
        if not hasattr(self, 'batch_edit_tab') or not self.batch_edit_tab.configs:
            QMessageBox.warning(self, "警告", "请先导入 KLE 布局数据并在批量编辑界面进行配置")
            return
        
        # 创建配置集合
        config_set = KeycapConfigSet()
        
        # 获取默认字体
        single_params = self.parameter_panel.get_parameters()
        default_font = single_params.font_path
        
        # 将每个批量编辑配置转换为 KeycapConfig
        for type_id, batch_config in self.batch_edit_tab.configs.items():
            # 从该类型中取第一个按键作为示例（用于获取labels）
            if type_id in self.batch_edit_tab.type_map:
                indices = self.batch_edit_tab.type_map[type_id]
                if indices and indices[0] < len(self.batch_edit_tab.kle_keys):
                    example_key = self.batch_edit_tab.kle_keys[indices[0]]
                    
                    # 创建几何参数
                    geometry = batch_config.geometry
                    geometry.key_width = u_to_mm(batch_config.key_type.width)
                    geometry.key_height = u_to_mm(batch_config.key_type.height)
                    
                    # 创建文本参数（使用实际字符，而不是X）
                    text_items = []
                    key_width_mm = geometry.key_width
                    key_height_mm = geometry.key_height
                    
                    for pos_idx in batch_config.key_type.label_positions:
                        # 获取该位置的字符（从示例按键）
                        if pos_idx < len(example_key.labels) and example_key.labels[pos_idx]:
                            label_text = example_key.labels[pos_idx]
                        else:
                            label_text = "X"  # 如果没有字符，使用X
                        
                        style = batch_config.get_style_for_position(pos_idx, default_font)
                        base_x, base_y = _calculate_base_position(pos_idx, key_width_mm, key_height_mm)
                        
                        text_param = TextParameters(
                            text=label_text,
                            font_path=style.font_path or default_font,
                            size=style.size,
                            depth=style.depth,
                            offset_x=base_x + style.offset_x,
                            offset_y=base_y + style.offset_y
                        )
                        text_items.append(text_param)
                    
                    # 创建设计
                    design = KeycapDesign(geometry=geometry, text_items=text_items)
                    
                    # 创建配置
                    key_type = batch_config.key_type
                    config = KeycapConfig(
                        geometry=geometry,
                        text_items=text_items,
                        key_type=key_type
                    )
                    
                    # 添加到集合
                    config_set.add_config(type_id, config)
        
        if not config_set.configs:
            QMessageBox.warning(self, "警告", "没有可导出的配置")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出整套按键配置",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        # 确保文件扩展名
        if not file_path.endswith('.json'):
            file_path += '.json'
        
        # 保存配置
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(config_set.to_json(indent=2))
            QMessageBox.information(
                self, 
                "导出成功", 
                f"整套按键配置已导出到:\n{file_path}\n\n包含 {len(config_set.configs)} 个按键类型"
            )
            self.status_bar.showMessage(f"整套按键配置已导出: {len(config_set.configs)} 个类型")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"无法导出配置:\n{str(e)}")
            print(f"导出配置失败: {e}")
            import traceback
            traceback.print_exc()
    
    def import_key_config(self):
        """导入按键配置"""
        from core.keycap_config import KeycapConfig, KeycapConfigSet
        from core.batch_edit_config import BatchEditConfig
        from core.legend_mapping import LegendStyle
        from core.parameters import KeycapGeometry
        
        # 选择文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入按键配置",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            # 尝试解析为配置集合
            try:
                config_set = KeycapConfigSet.from_json(json_str)
                is_set = True
            except:
                # 如果不是集合，尝试解析为单个配置
                try:
                    single_config = KeycapConfig.from_json(json_str)
                    # 转换为集合格式
                    config_set = KeycapConfigSet()
                    # 使用key_type作为type_id
                    type_id = single_config.key_type.to_string()
                    config_set.add_config(type_id, single_config)
                    is_set = False
                except Exception as e:
                    QMessageBox.warning(self, "导入失败", f"无法解析配置文件:\n{str(e)}")
                    return
            
            # 检查是否有KLE数据
            if not hasattr(self, 'batch_edit_tab') or not self.batch_edit_tab.kle_keys:
                QMessageBox.warning(self, "警告", "请先导入 KLE 布局数据")
                return
            
            # 应用配置到批量编辑界面
            applied_count = 0
            for type_id, config in config_set.configs.items():
                # 检查该类型是否存在于当前KLE数据中
                if type_id in self.batch_edit_tab.type_map:
                    # 将 KeycapConfig 转换为 BatchEditConfig
                    batch_config = BatchEditConfig(
                        key_type=config.key_type,
                        geometry=config.geometry
                    )
                    
                    # 将 TextParameters 转换为 LegendStyle
                    # 需要根据位置索引匹配，并计算offset
                    from core.legend_mapping import _calculate_base_position
                    from core.keycap_presets import u_to_mm
                    
                    key_width_mm = u_to_mm(config.key_type.width)
                    key_height_mm = u_to_mm(config.key_type.height)
                    pos_indices = sorted(config.key_type.label_positions)
                    
                    # 为每个位置创建样式
                    for i, pos_idx in enumerate(pos_indices):
                        if i < len(config.text_items):
                            tp = config.text_items[i]
                            # 计算base_position
                            base_x, base_y = _calculate_base_position(pos_idx, key_width_mm, key_height_mm)
                            # 计算offset（从总offset中减去base_position）
                            offset_x = tp.offset_x - base_x
                            offset_y = tp.offset_y - base_y
                            
                            # 创建LegendStyle
                            style = LegendStyle(
                                font_path=tp.font_path,
                                size=tp.size,
                                depth=tp.depth,
                                offset_x=offset_x,
                                offset_y=offset_y,
                                rotation=tp.rotation if hasattr(tp, 'rotation') else 0.0
                            )
                            batch_config.set_style_for_position(pos_idx, style)
                    
                    # 更新配置
                    self.batch_edit_tab.configs[type_id] = batch_config
                    applied_count += 1
            
            if applied_count > 0:
                # 刷新批量编辑界面
                if self.batch_edit_tab.current_type_id in self.batch_edit_tab.configs:
                    current_config = self.batch_edit_tab.configs[self.batch_edit_tab.current_type_id]
                    self.batch_edit_tab.edit_panel.load_type(current_config.key_type, current_config)
                    self.batch_edit_tab.preview_2d.update_preview(current_config.key_type, current_config)
                    self.batch_edit_tab._update_3d_preview(current_config)
                
                # 发出配置应用信号
                self.batch_edit_tab.config_applied.emit(self.batch_edit_tab.configs.copy())
                
                QMessageBox.information(
                    self,
                    "导入成功",
                    f"已导入 {applied_count} 个按键类型配置\n\n"
                    f"文件: {file_path}"
                )
                self.status_bar.showMessage(f"已导入 {applied_count} 个按键类型配置")
            else:
                QMessageBox.warning(
                    self,
                    "导入失败",
                    "配置文件中没有匹配当前KLE布局的按键类型"
                )
        
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"无法导入配置:\n{str(e)}")
            print(f"导入配置失败: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        # 新建
        new_action = QAction("新建(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        # 导出STL
        export_stl_action = QAction("导出STL(&S)", self)
        export_stl_action.setShortcut("Ctrl+S")
        export_stl_action.triggered.connect(self.export_stl)
        file_menu.addAction(export_stl_action)
        
        # 导出STEP
        export_step_action = QAction("导出STEP(&P)", self)
        export_step_action.setShortcut("Ctrl+P")
        export_step_action.triggered.connect(self.export_step)
        file_menu.addAction(export_step_action)
        
        # 导出3MF（推荐用于多色打印）
        export_3mf_action = QAction("导出3MF(&M) [推荐多色]", self)
        export_3mf_action.setShortcut("Ctrl+M")
        export_3mf_action.triggered.connect(self.export_3mf)
        file_menu.addAction(export_3mf_action)
        
        file_menu.addSeparator()
        
        # 导入 KLE 布局数据
        import_kle_action = QAction("导入 KLE 布局数据(&K)...", self)
        import_kle_action.setShortcut("Ctrl+K")
        import_kle_action.triggered.connect(self.import_kle_layout)
        file_menu.addAction(import_kle_action)
        
        # 导出单个按键配置
        export_single_config_action = QAction("导出单个按键配置(&C)...", self)
        export_single_config_action.triggered.connect(self.export_single_key_config)
        file_menu.addAction(export_single_config_action)
        
        # 导出整套按键配置
        export_all_config_action = QAction("导出整套按键配置(&A)...", self)
        export_all_config_action.triggered.connect(self.export_all_key_configs)
        file_menu.addAction(export_all_config_action)
        
        # 导入按键配置
        import_config_action = QAction("导入按键配置(&I)...", self)
        import_config_action.triggered.connect(self.import_key_config)
        file_menu.addAction(import_config_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单（吸附设置）
        view_menu = menubar.addMenu("视图(&V)")
        
        self.snap_action_enable = QAction("启用对齐吸附", self, checkable=True)
        self.snap_action_enable.setChecked(self.settings.get_snap_enabled())
        self.snap_action_enable.triggered.connect(self.toggle_snap)
        view_menu.addAction(self.snap_action_enable)
        
        # 网格大小子菜单
        grid_menu = view_menu.addMenu("网格大小")
        grid_sizes = [0.1, 0.5, 1.0, 2.0, 5.0]
        self.grid_actions = []
        current_grid = self.settings.get_snap_grid_size()
        
        grid_group = QActionGroup(self)
        for size in grid_sizes:
            action = QAction(f"{size} mm", self, checkable=True)
            if abs(size - current_grid) < 0.001:
                action.setChecked(True)
            action.setData(size)
            action.triggered.connect(lambda c, s=size: self.set_grid_size(s))
            grid_group.addAction(action)
            grid_menu.addAction(action)
            self.grid_actions.append(action)

        # 对齐菜单（预设位置）
        align_menu = menubar.addMenu("对齐(&A)")
        positions = [
            ("左上", "左上"), ("中上", "中上"), ("右上", "右上"),
            ("左中", "左中"), ("中间", "中间"), ("右中", "右中"),
            ("左下", "左下"), ("中下", "中下"), ("右下", "右下")
        ]
        for name, preset in positions:
            action = QAction(name, self)
            action.triggered.connect(lambda c, p=preset: self.preview_2d_widget.apply_preset_position(p))
            align_menu.addAction(action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        
        settings_action = QAction("设置(&S)...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def toggle_snap(self, checked):
        """切换吸附"""
        self.preview_2d_widget.set_snap_enabled(checked)
        self.settings.set_snap_enabled(checked)
        
    def set_grid_size(self, size):
        """设置网格大小"""
        self.preview_2d_widget.set_snap_grid_size(size)
        self.settings.set_snap_grid_size(size)
    
    def setup_statusbar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def on_parameters_changed(self, params: KeycapParameters):
        """参数改变时的处理"""
        # 更新2D预览的按键尺寸
        self.preview_2d_widget.set_key_size(params.key_width, params.key_height)
        # 更新2D预览的几何参数
        self.preview_2d_widget.set_key_geometry(params.key_depth, params.side_angle)
        
        # 确保字体路径已设置（如果选择了字体）
        if params.font_path is None and self.parameter_panel.font_combo.currentIndex() >= 0:
            font_path = self.parameter_panel.font_combo.currentData()
            if font_path:
                params.font_path = font_path
        
        # 更新预览字体
        if params.font_path:
            self.preview_2d_widget.set_font(params.font_path)
        
        # 如果有选中的文字项，实时更新其大小
        selected_index = self.preview_2d_widget.selected_index
        if selected_index >= 0 and selected_index < len(self.preview_2d_widget.text_items):
            item = self.preview_2d_widget.text_items[selected_index]
            # 更新选中项的字体大小
            item.font_size = params.text_height
            self.preview_2d_widget.update()
            # 触发内容改变信号以触发自动更新
            self.preview_2d_widget.content_changed.emit()
            
        # 尝试自动更新
        self.check_auto_update()

    def check_auto_update(self):
        """检查并执行自动更新"""
        if self.settings.get_auto_update():
            # 重置定时器（防抖），延迟执行
            self.update_timer.start()
    
    def on_insert_text(self, text: str, font_size: float):
        """插入文字到2D预览"""
        index = self.preview_2d_widget.add_text(text, font_size)
        # 更新参数中的文字
        self.parameter_panel.params.letter = text
        self.parameter_panel.params.text_height = font_size
        
        self.check_auto_update()
    
    def on_text_position_changed(self, index: int, x: float, y: float):
        """文字位置改变"""
        # 更新参数中的文字偏移
        if index < len(self.preview_2d_widget.text_items):
            item = self.preview_2d_widget.text_items[index]
            self.parameter_panel.params.text_offset_x = item.x
            self.parameter_panel.params.text_offset_y = item.y
            self.parameter_panel.params.letter = item.text
            self.parameter_panel.params.text_height = item.font_size
            
            # 实时更新3D预览位置
            # 只有当单字符时才执行，避免多字符整体移动
            if len(self.preview_2d_widget.text_items) > 1:
                return

            if self.last_generated_text_pos and self.preview_widget.text_actor:
                gen_x, gen_y = self.last_generated_text_pos
                dx = item.x - gen_x
                dy = item.y - gen_y
                self.preview_widget.update_text_offset(dx, dy)

    def generate_model(self):
        """生成模型"""
        params = self.parameter_panel.get_parameters()
        
        # 确保字体路径已设置（从参数面板获取）
        if params.font_path is None and self.parameter_panel.font_combo.currentIndex() >= 0:
            font_path = self.parameter_panel.font_combo.currentData()
            if font_path:
                params.font_path = font_path
        
        # 从2D预览同步所有文字项到参数
        # 这解决了多文字生成问题，并确保位置与预览完全一致
        params.text_items = []
        for item in self.preview_2d_widget.text_items:
            # 创建 TextParameters 对象
            text_param = TextParameters(
                text=item.text,
                size=item.font_size,
                offset_x=item.x,
                offset_y=item.y,
                # 默认深度为参数面板中的设置
                depth=params.text_depth,
                # 重要：必须设置字体路径（使用 params.font_path，如果为空则尝试从面板获取）
                font_path=params.font_path or (self.parameter_panel.font_combo.currentData() if self.parameter_panel.font_combo.currentIndex() >= 0 else None)
            )
            params.text_items.append(text_param)
        
        # 如果没有 text_items，但 letter 有值，创建一个默认项
        if not params.text_items and params.letter:
            text_param = TextParameters(
                text=params.letter,
                size=params.text_height,
                offset_x=params.text_offset_x,
                offset_y=params.text_offset_y,
                depth=params.text_depth,
                font_path=params.font_path or (self.parameter_panel.font_combo.currentData() if self.parameter_panel.font_combo.currentIndex() >= 0 else None)
            )
            params.text_items.append(text_param)
        
        # 验证参数
        is_valid, error_msg = params.validate()
        if not is_valid:
            QMessageBox.warning(self, "参数错误", error_msg)
            return
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.status_bar.showMessage("正在生成模型...")
        
        # 在后台线程中生成模型
        self.gen_thread = ModelGenerationThread(params)
        self.gen_thread.finished.connect(self.on_model_generated)
        self.gen_thread.error.connect(self.on_generation_error)
        self.gen_thread.start()
    
    def on_model_generated(self, keycap_model, text_model):
        """模型生成完成"""
        self.current_keycap_model = keycap_model
        self.current_text_model = text_model
        
        # 记录生成时的文字位置，用于后续实时预览
        params = self.gen_thread.params
        self.last_generated_text_pos = (params.text_offset_x, params.text_offset_y)
        
        # 更新预览
        self.preview_widget.update_model(keycap_model, text_model)
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("模型生成完成")
        
        if keycap_model is None:
            QMessageBox.warning(self, "生成失败", "无法生成按键模型，请检查参数设置。")
        elif text_model is None and self.parameter_panel.params.font_path:
            QMessageBox.information(self, "提示", "按键模型生成成功，但文字模型生成失败。")
    
    def on_generation_error(self, error_msg: str):
        """生成错误"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("生成失败")
        QMessageBox.critical(self, "错误", f"生成模型时出错:\n{error_msg}")
    
    def new_project(self):
        """新建项目"""
        # 重置参数面板
        self.parameter_panel.letter_edit.setText("A")
        self.parameter_panel.width_spin.setValue(18.0)
        self.parameter_panel.height_spin.setValue(18.0)
        self.parameter_panel.depth_spin.setValue(8.0)
        self.parameter_panel.wall_spin.setValue(1.0)
        self.parameter_panel.side_angle_spin.setValue(0.0)
        self.parameter_panel.text_height_spin.setValue(3.0)
        self.parameter_panel.text_depth_spin.setValue(0.5)
        
        # 清除预览
        self.preview_widget.clear()
        self.preview_2d_widget.clear_texts()
        self.preview_2d_widget.add_text("A", 3.0)
        
        self.current_keycap_model = None
        self.current_text_model = None
        self.last_generated_text_pos = None
        
        self.status_bar.showMessage("已重置")
    
    def export_stl(self):
        """导出STL文件"""
        if self.current_keycap_model is None:
            QMessageBox.warning(self, "警告", "请先生成模型。")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出STL文件",
            "",
            "STL文件 (*.stl);;所有文件 (*.*)"
        )
        
        if file_path:
            # 移除扩展名
            base_path = file_path.rsplit('.', 1)[0]
            
            # 导出
            keycap_success, text_success = export_stl_keycap_text(
                self.current_keycap_model,
                self.current_text_model,
                base_path
            )
            
            if keycap_success:
                fname = os.path.basename(base_path)
                msg = f"按键模型已导出: {fname}_keycap.stl"
                
                if text_success:
                    msg += f"\n文字模型已导出: {fname}_text.stl"
                    msg += "\n\n【多色打印提示】\n请将这两个文件同时拖入切片软件（如选择“作为单一对象加载”），以进行多色打印设置。"
                    QMessageBox.information(self, "导出成功", msg)
                else:
                    self.status_bar.showMessage(msg)
            else:
                QMessageBox.warning(self, "导出失败", "无法导出STL文件。")
    
    def export_step(self):
        """导出STEP文件"""
        if self.current_keycap_model is None:
            QMessageBox.warning(self, "警告", "请先生成模型。")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出STEP文件",
            "",
            "STEP文件 (*.step *.stp);;所有文件 (*.*)"
        )
        
        if file_path:
            # 移除扩展名
            base_path = file_path.rsplit('.', 1)[0]
            
            # 导出
            keycap_success, text_success = export_step_keycap_text(
                self.current_keycap_model,
                self.current_text_model,
                base_path
            )
            
            if keycap_success:
                fname = os.path.basename(base_path)
                msg = f"按键模型已导出: {fname}_keycap.step"
                
                if text_success:
                    msg += f"\n文字模型已导出: {fname}_text.step"
                    msg += "\n\nSTEP文件也已拆分为两个独立文件以便于CAD处理。"
                    QMessageBox.information(self, "导出成功", msg)
                else:
                    self.status_bar.showMessage(msg)
            else:
                QMessageBox.warning(self, "导出失败", "无法导出STEP文件。")
    
    def export_3mf(self):
        """导出3MF文件（推荐用于多色打印）"""
        if self.current_keycap_model is None:
            QMessageBox.warning(self, "警告", "请先生成模型。")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出3MF文件",
            "",
            "3MF文件 (*.3mf);;所有文件 (*.*)"
        )
        
        if file_path:
            # 确保扩展名正确
            if not file_path.lower().endswith('.3mf'):
                file_path += '.3mf'
            
            # 导出
            success = export_3mf(
                self.current_keycap_model,
                self.current_text_model,
                file_path
            )
            
            if success:
                fname = os.path.basename(file_path)
                msg = f"3MF文件已导出: {fname}\n\n"
                msg += "【多色打印优势】\n"
                msg += "✓ 单个文件包含按键和文字两个部件\n"
                msg += "✓ 自动保留颜色信息（按键=深灰，文字=白色）\n"
                msg += "✓ 直接拖入切片软件即可识别多部件\n"
                msg += "✓ 无需手动对齐或合并文件"
                QMessageBox.information(self, "导出成功", msg)
            else:
                error_msg = "无法导出3MF文件。\n\n"
                error_msg += "可能原因：缺少 trimesh 库\n"
                error_msg += "解决方法：在终端运行 pip install trimesh"
                QMessageBox.warning(self, "导出失败", error_msg)
    
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新2D预览的对齐设置
            snap_enabled = self.settings.get_snap_enabled()
            snap_grid = self.settings.get_snap_grid_size()
            
            self.preview_2d_widget.set_snap_enabled(snap_enabled)
            self.preview_2d_widget.set_snap_grid_size(snap_grid)
            
            # 更新菜单状态
            self.snap_action_enable.setChecked(snap_enabled)
            for action in self.grid_actions:
                if abs(action.data() - snap_grid) < 0.001:
                    action.setChecked(True)
    
    def load_settings(self):
        """加载设置"""
        # 设置已经在初始化时加载
        pass
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "机械键盘按键模型生成器\n\n"
            "版本: 1.0.0\n\n"
            "一个参数化的机械键盘按键3D模型生成工具，\n"
            "支持自定义字体、字母和按键参数，\n"
            "生成分离的按键和文字模型，便于多色3D打印。"
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        # 清理资源，避免退出时报错
        try:
            # 停止定时器
            if hasattr(self, 'update_timer'):
                self.update_timer.stop()
            
            # 停止生成线程（如果正在运行）
            if hasattr(self, 'gen_thread') and self.gen_thread.isRunning():
                self.gen_thread.terminate()
                self.gen_thread.wait()
            
            # 清理 VTK 组件（避免退出时的警告）
            if hasattr(self, 'preview_widget') and self.preview_widget:
                try:
                    self.preview_widget.vtk_widget.GetRenderWindow().Finalize()
                except:
                    pass
            
            if hasattr(self, 'batch_preview_widget') and self.batch_preview_widget:
                try:
                    self.batch_preview_widget.vtk_widget.GetRenderWindow().Finalize()
                except:
                    pass
            
            # 清理批量编辑界面的3D预览
            if hasattr(self, 'batch_edit_tab') and self.batch_edit_tab:
                if hasattr(self.batch_edit_tab, 'preview_3d') and self.batch_edit_tab.preview_3d:
                    try:
                        self.batch_edit_tab.preview_3d.vtk_widget.GetRenderWindow().Finalize()
                    except:
                        pass
                    
        except Exception as e:
            # 忽略清理时的错误，确保窗口能正常关闭
            print(f"清理资源时出错（可忽略）: {e}")
        
        event.accept()
