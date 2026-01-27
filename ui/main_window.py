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
from core.parameters import KeycapParameters, TextParameters, ImageParameters
from core.keycap_modeler import KeycapModeler
from core.settings import Settings
from export.stl_exporter import export_keycap_and_text as export_stl_keycap_text
from export.step_exporter import export_keycap_and_text as export_step_keycap_text
from export.threemf_exporter import export_3mf
import cadquery as cq
import os


class ModelGenerationThread(QThread):
    """模型生成线程（避免UI阻塞）"""
    
    finished = pyqtSignal(object, object, object)  # (keycap_model, text_model, image_inlay)
    error = pyqtSignal(str)
    
    def __init__(self, params: KeycapParameters):
        super().__init__()
        self.params = params
    
    def run(self):
        """运行模型生成"""
        try:
            modeler = KeycapModeler(self.params)
            keycap_model, text_model, image_inlay = modeler.generate()
            self.finished.emit(keycap_model, text_model, image_inlay)
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


class BatchExportThread(QThread):
    """批量导出后台线程（避免生成/合并/3MF 导出阻塞主线程导致界面卡死）"""
    progress = pyqtSignal(int, int)  # current, total
    progress_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str)  # success, detail_msg(for dialog), status_msg
    error = pyqtSignal(str)

    def __init__(self, mode, path, kle_keys, batch_configs, default_geometry, default_font,
                 row_spacing, col_spacing, row_heights, use_height_profile):
        super().__init__()
        self.mode = mode
        self.path = path
        self.kle_keys = kle_keys
        self.batch_configs = batch_configs or {}
        self.default_geometry = default_geometry
        self.default_font = default_font
        self.row_spacing = float(row_spacing)
        self.col_spacing = float(col_spacing)
        self.row_heights = dict(row_heights) if row_heights else {}
        self.use_height_profile = bool(use_height_profile)

    def run(self):
        try:
            from core.batch_generator import BatchGenerator
            from core.legend_mapping import LegendMapping
            from core.key_type_analyzer import KeyTypeAnalyzer
            from core.keycap_presets import u_to_mm
            from export.stl_exporter import export_keycap_and_text
            from export.step_exporter import export_keycap_and_text as export_step_keycap_text
            from export.threemf_exporter import export_3mf
            import os

            n = len(self.kle_keys)
            if n == 0:
                self.finished.emit(False, "没有可导出的按键", "导出取消")
                return

            if self.mode == "separate":
                success_count = 0
                for i, kle_key in enumerate(self.kle_keys):
                    self.progress.emit(i + 1, n)
                    self.progress_message.emit(f"正在生成按键 {i+1}/{n}...")
                    batch_config = self.batch_configs.get(
                        KeyTypeAnalyzer.get_signature_for_key(kle_key).to_string()
                    )
                    global_geometry, legend_mapping = self._get_geometry_and_mapping(kle_key, batch_config)
                    generator = BatchGenerator(global_geometry, legend_mapping)
                    generator.set_default_font(self.default_font)
                    keycap_model, text_model = generator.generate_single_key(kle_key)
                    if keycap_model:
                        main_label = (kle_key.labels[9] if len(kle_key.labels) > 9 and kle_key.labels[9]
                                      else kle_key.labels[0] if kle_key.labels else "Key")
                        safe_label = "".join(c for c in str(main_label) if c.isalnum() or c in (' ', '-', '_'))[:10]
                        filename = f"Key_R{getattr(kle_key, 'row', 0)}_{i+1:02d}_{safe_label}"
                        base_path = os.path.join(self.path, filename)
                        k_success, _, _ = export_keycap_and_text(keycap_model, text_model, base_path)
                        if k_success:
                            success_count += 1
                self.finished.emit(
                    True,
                    f"已导出 {success_count} 个按键到:\n{self.path}",
                    f"导出完成：成功 {success_count}/{n} 个按键"
                )
                return

            # 合并导出
            row_spacing, col_spacing = self.row_spacing, self.col_spacing
            sorted_keys = sorted(self.kle_keys, key=lambda k: (k.y, k.x))
            rows = {}
            for k in sorted_keys:
                y = k.y
                rows.setdefault(y, []).append(k)
            sorted_rows = sorted(rows.keys())
            first_row_max_height = 0.0
            if sorted_rows:
                for key in rows[sorted_rows[0]]:
                    first_row_max_height = max(first_row_max_height, u_to_mm(key.height))
            current_y = first_row_max_height / 2
            max_row_height = 0.0
            all_keycaps, all_texts = [], []

            for row_idx, row_y in enumerate(sorted_rows):
                row_keys = sorted(rows[row_y], key=lambda k: k.x)
                current_x = 0.0
                for i, kle_key in enumerate(row_keys):
                    done = len(all_keycaps) + 1
                    self.progress.emit(done, n)
                    self.progress_message.emit(f"正在生成按键 {done}/{n}...")
                    batch_config = self.batch_configs.get(
                        KeyTypeAnalyzer.get_signature_for_key(kle_key).to_string()
                    )
                    global_geometry, legend_mapping = self._get_geometry_and_mapping(kle_key, batch_config)
                    generator = BatchGenerator(global_geometry, legend_mapping)
                    generator.set_default_font(self.default_font)
                    keycap_model, text_model = generator.generate_single_key(kle_key)
                    if keycap_model:
                        kw = u_to_mm(kle_key.width)
                        kh = u_to_mm(kle_key.height)
                        cx = current_x + kw / 2
                        cy = current_y - kh / 2
                        keycap_pos = keycap_model.translate((cx, cy, 0))
                        text_pos = text_model.translate((cx, cy, 0)) if text_model else None
                        all_keycaps.append(keycap_pos)
                        if text_pos:
                            all_texts.append(text_pos)
                        current_x += kw + col_spacing
                        max_row_height = max(max_row_height, kh)
                if row_idx < len(sorted_rows) - 1:
                    current_y -= max_row_height + row_spacing
                    max_row_height = 0.0

            if not all_keycaps:
                self.finished.emit(False, "没有成功生成任何按键", "批量导出完成")
                return

            self.progress_message.emit("正在合并键帽模型，请稍候...")
            merged_keycap = all_keycaps[0]
            for k in all_keycaps[1:]:
                merged_keycap = merged_keycap.union(k)
            merged_text = None
            if all_texts:
                self.progress_message.emit("正在合并字符模型，请稍候...")
                merged_text = all_texts[0]
                for t in all_texts[1:]:
                    if t:
                        merged_text = merged_text.union(t)

            path = self.path
            file_ext = os.path.splitext(path)[1].lower()
            self.progress_message.emit("正在写入文件，请稍候...")
            if file_ext == '.stl':
                base_path = os.path.splitext(path)[0]
                k_ok, _, _ = export_keycap_and_text(merged_keycap, merged_text, base_path)
                if k_ok:
                    self.finished.emit(True, f"已导出合并文件到:\n{base_path}_keycap.stl\n{base_path}_text.stl", "批量导出完成")
                else:
                    self.finished.emit(False, "STL 导出失败", "批量导出完成")
            elif file_ext in ['.step', '.stp']:
                base_path = os.path.splitext(path)[0]
                k_ok, _, _ = export_step_keycap_text(merged_keycap, merged_text, base_path)
                if k_ok:
                    self.finished.emit(True, f"已导出合并文件到:\n{base_path}_keycap.step\n{base_path}_text.step", "批量导出完成")
                else:
                    self.finished.emit(False, "STEP 导出失败", "批量导出完成")
            elif file_ext == '.3mf':
                ok = export_3mf(merged_keycap, merged_text, path)
                if ok:
                    self.finished.emit(True, f"已导出合并文件到:\n{path}", "批量导出完成")
                else:
                    self.finished.emit(False, "3MF 导出失败", "批量导出完成")
            else:
                self.finished.emit(False, f"不支持的文件格式: {file_ext}", "批量导出完成")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _get_geometry_and_mapping(self, kle_key, batch_config):
        from core.legend_mapping import LegendMapping, LegendStyle
        from copy import deepcopy
        row_heights = self.row_heights if self.use_height_profile else {}
        if batch_config:
            g = batch_config.geometry
            if row_heights and kle_key.y in row_heights:
                g = deepcopy(g)
                g.key_depth = row_heights[kle_key.y]
            if not hasattr(g, 'stabilizer_enabled'):
                g.stabilizer_enabled = getattr(batch_config.geometry, 'stabilizer_enabled', False)
            if not hasattr(g, 'stabilizer_length'):
                g.stabilizer_length = getattr(batch_config.geometry, 'stabilizer_length', 50.0)
            lm = LegendMapping()
            for pos_idx, style in batch_config.text_styles.items():
                s = LegendStyle(
                    font_path=style.font_path or self.default_font,
                    size=getattr(style, 'size', 3.0),
                    offset_x=getattr(style, 'offset_x', 0.0),
                    offset_y=getattr(style, 'offset_y', 0.0),
                    depth=getattr(style, 'depth', 0.5),
                    rotation=getattr(style, 'rotation', 0.0),
                    stroke_width=getattr(style, 'stroke_width', 0.0),
                    bold=getattr(style, 'bold', False),
                    italic=getattr(style, 'italic', False),
                    underline=getattr(style, 'underline', False)
                )
                lm.set_style(pos_idx, s)
            return g, lm
        g = self.default_geometry
        if row_heights and kle_key.y in row_heights:
            g = deepcopy(g)
            g.key_depth = row_heights[kle_key.y]
        lm = LegendMapping.create_default()
        if self.default_font:
            for style in lm.mapping.values():
                if style.font_path is None:
                    style.font_path = self.default_font
        return g, lm


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_keycap_model = None
        self.current_text_model = None
        self.current_image_inlay = None
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
        self.parameter_panel.insert_image_signal.connect(self.on_insert_image)
        single_key_layout.addWidget(self.parameter_panel, stretch=1)
        
        # 右侧预览区域
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(5)
        
        # 2D 预览
        self.preview_2d_widget = Preview2DWidget()
        self.preview_2d_widget.text_position_changed.connect(self.on_text_position_changed)
        self.preview_2d_widget.selection_changed.connect(self.on_2d_selection_changed)
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
        
        # ===== Tab 1: 键盘设计（左右布局） =====
        # 左侧：2D预览、模型间距(在2D下方)、功能按钮、3D预览；右侧：按键属性、高度类型
        batch_widget = QWidget()
        batch_main = QHBoxLayout(batch_widget)
        batch_main.setSpacing(8)
        batch_main.setContentsMargins(8, 8, 8, 8)
        
        self.batch_panel = BatchPanel()
        self.batch_panel.kle_data_changed.connect(self.on_kle_data_changed)
        self.batch_panel.generate_batch_signal.connect(self.on_generate_batch)
        self.batch_panel.generate_all_signal.connect(self.on_generate_all_keys)
        self.batch_panel.export_all_signal.connect(self.on_export_all)
        
        # 左侧列（竖排）：2D 4 / 模型间距 1（在2D下方）/ 按钮 1 / 3D 4
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        self.kle_preview_widget = KLEPreviewWidget()
        self.kle_preview_widget.key_selected.connect(self.on_kle_key_selected)
        left_col.addWidget(self.kle_preview_widget, stretch=4)
        left_col.addWidget(self.batch_panel.get_spacing_widget(), stretch=1)
        left_col.addWidget(self.batch_panel.get_actions_widget(), stretch=1)
        self.batch_preview_widget = PreviewWidget()
        left_col.addWidget(self.batch_preview_widget, stretch=4)
        
        left_wrap = QWidget()
        left_wrap.setLayout(left_col)
        batch_main.addWidget(left_wrap, stretch=7)  # 左侧占70%
        
        # 右侧列（竖排）：上=按键属性，下=高度类型
        from ui.key_property_panel import KeyPropertyPanel
        self.key_property_panel = KeyPropertyPanel()
        self.key_property_panel.data_updated.connect(self.on_kle_key_updated_and_preview)
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        right_col.addWidget(self.key_property_panel, stretch=1)
        right_col.addWidget(self.batch_panel.get_height_widget(), stretch=1)
        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        batch_main.addWidget(right_wrap, stretch=3)  # 右侧占30%
        
        self.mode_tabs.addTab(batch_widget, "键盘设计")
        
        # ===== Tab 2: 键盘参数 =====
        from ui.batch_edit_tab import BatchEditTab
        self.batch_edit_tab = BatchEditTab()
        self.batch_edit_tab.config_applied.connect(self.on_batch_config_applied)
        self.mode_tabs.addTab(self.batch_edit_tab, "键盘参数")
        
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
        # 2D 预览使用固定 0 间距，不随模型间距变化
        
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
        """在后台线程执行批量导出，避免主线程阻塞导致界面卡死"""
        batch_configs = {}
        if hasattr(self, 'batch_edit_tab'):
            batch_configs = self.batch_edit_tab.get_configs()
        single_params = self.parameter_panel.get_parameters()
        default_geometry = single_params.geometry
        default_font = single_params.font_path
        if not default_font:
            from utils.font_utils import find_times_new_roman
            default_font = find_times_new_roman()
        kle_keys = self.kle_preview_widget.keys
        row_spacing = getattr(self.batch_panel, 'row_spacing', 2.0)
        col_spacing = getattr(self.batch_panel, 'col_spacing', 2.0)
        use_height_profile = getattr(self.batch_panel, 'use_height_profile', False)
        row_heights = getattr(self.batch_panel, 'row_heights', {}) or {}

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(kle_keys))
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("正在批量生成...")

        thread = BatchExportThread(
            mode, path, kle_keys, batch_configs,
            default_geometry, default_font,
            row_spacing, col_spacing, row_heights, use_height_profile
        )
        thread.progress.connect(self._on_batch_export_progress)
        thread.progress_message.connect(self.status_bar.showMessage)
        thread.finished.connect(self._on_batch_export_finished)
        thread.error.connect(self._on_batch_export_error)
        self._batch_export_thread = thread
        thread.start()

    def _on_batch_export_progress(self, current: int, total: int):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def _on_batch_export_finished(self, success: bool, detail_msg: str, status_msg: str):
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(status_msg)
        if success:
            QMessageBox.information(self, "导出完成", detail_msg)
        else:
            QMessageBox.warning(self, "导出完成", detail_msg)

    def _on_batch_export_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("导出失败")
        QMessageBox.critical(self, "导出失败", f"批量导出时发生错误:\n\n{msg}")
    
    def export_single_key_config(self):
        """导出单个按键配置"""
        from core.keycap_config import KeycapConfig
        from core.batch_generator import BatchGenerator
        from core.legend_mapping import LegendMapping, LegendStyle, _calculate_base_position, get_top_surface_size
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
                        top_w, top_h = get_top_surface_size(
                            key_width_mm, key_height_mm,
                            geometry.key_depth,
                            getattr(geometry, 'side_angle', 0.0) or 0.0
                        )
                        for pos_idx in batch_config.key_type.label_positions:
                            style = batch_config.get_style_for_position(pos_idx, single_params.font_path)
                            base_x, base_y = _calculate_base_position(
                                pos_idx, key_width_mm, key_height_mm,
                                top_width=top_w, top_height=top_h
                            )
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
        from core.legend_mapping import LegendMapping, LegendStyle, _calculate_base_position, get_top_surface_size
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
                    
                    # 创建文本参数（使用实际字符，而不是X）；按顶面尺寸放置
                    text_items = []
                    key_width_mm = geometry.key_width
                    key_height_mm = geometry.key_height
                    top_w, top_h = get_top_surface_size(
                        key_width_mm, key_height_mm,
                        geometry.key_depth,
                        getattr(geometry, 'side_angle', 0.0) or 0.0
                    )
                    for pos_idx in batch_config.key_type.label_positions:
                        # 获取该位置的字符（从示例按键）
                        if pos_idx < len(example_key.labels) and example_key.labels[pos_idx]:
                            label_text = example_key.labels[pos_idx]
                        else:
                            label_text = "X"  # 如果没有字符，使用X
                        
                        style = batch_config.get_style_for_position(pos_idx, default_font)
                        base_x, base_y = _calculate_base_position(
                            pos_idx, key_width_mm, key_height_mm,
                            top_width=top_w, top_height=top_h
                        )
                        
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
                    # 需要根据位置索引匹配，并计算offset（按顶面尺寸算 base，与导出时一致）
                    from core.legend_mapping import _calculate_base_position, get_top_surface_size
                    from core.keycap_presets import u_to_mm
                    
                    key_width_mm = u_to_mm(config.key_type.width)
                    key_height_mm = u_to_mm(config.key_type.height)
                    g = config.geometry
                    top_w, top_h = get_top_surface_size(
                        key_width_mm, key_height_mm,
                        g.key_depth,
                        getattr(g, 'side_angle', 0.0) or 0.0
                    )
                    pos_indices = sorted(config.key_type.label_positions)
                    
                    # 为每个位置创建样式
                    for i, pos_idx in enumerate(pos_indices):
                        if i < len(config.text_items):
                            tp = config.text_items[i]
                            # 计算base_position
                            base_x, base_y = _calculate_base_position(
                                pos_idx, key_width_mm, key_height_mm,
                                top_width=top_w, top_height=top_h
                            )
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
        
        # 如果有选中的文字项，将左侧参数直接写回该字符，便于对已添加字符进行修改
        selected_index = self.preview_2d_widget.selected_index
        if selected_index >= 0 and selected_index < len(self.preview_2d_widget.text_items):
            item = self.preview_2d_widget.text_items[selected_index]
            item.text = params.letter or "A"
            item.font_size = params.text_height
            item.x = params.text_offset_x
            item.y = params.text_offset_y
            self.preview_2d_widget.update()
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
    
    def on_insert_image(self, path: str, size: float, scale: float = 1.0):
        """插入图片到2D预览"""
        depth = self.parameter_panel.params.text_depth
        self.preview_2d_widget.add_image(path, size=size, depth=depth, scale=scale)
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

    def on_2d_selection_changed(self, index: int):
        """2D 预览中选中项改变时，将选中字符的参数同步到左侧参数面板"""
        if index < 0 or index >= len(self.preview_2d_widget.text_items):
            return
        item = self.preview_2d_widget.text_items[index]
        self.parameter_panel.set_parameters_for_text_item(
            item.text, item.font_size, item.x, item.y
        )

    def generate_model(self):
        """生成模型"""
        params = self.parameter_panel.get_parameters()
        
        # 确保字体路径已设置（从参数面板获取）
        if params.font_path is None and self.parameter_panel.font_combo.currentIndex() >= 0:
            font_path = self.parameter_panel.font_combo.currentData()
            if font_path:
                params.font_path = font_path
        
        # 从2D预览同步所有文字项到参数，字体设置（线宽、加粗、斜体、下划线）从面板取值
        params.text_items = []
        stroke_width = self.parameter_panel.text_stroke_width_spin.value()
        bold = self.parameter_panel.text_bold_check.isChecked()
        italic = self.parameter_panel.text_italic_check.isChecked()
        underline = self.parameter_panel.text_underline_check.isChecked()
        for item in self.preview_2d_widget.text_items:
            text_param = TextParameters(
                text=item.text,
                size=item.font_size,
                offset_x=item.x,
                offset_y=item.y,
                depth=params.text_depth,
                stroke_width=stroke_width,
                bold=bold,
                italic=italic,
                underline=underline,
                font_path=params.font_path or (self.parameter_panel.font_combo.currentData() if self.parameter_panel.font_combo.currentIndex() >= 0 else None)
            )
            params.text_items.append(text_param)
        
        # 2D 预览为文字来源：若 2D 已清空所有文字则不再用 letter 补默认项，避免 3D 出现多余的 A
        # （旧逻辑：无 text_items 时用 letter 创建默认项，会在仅图片时产生 phantom "A"）
        
        # 从2D预览同步所有图片项到参数
        params.image_items = []
        for item in self.preview_2d_widget.image_items:
            ip = ImageParameters(
                path=item.path,
                depth=item.depth,
                offset_x=item.x,
                offset_y=item.y,
                size=item.size,
                scale=getattr(item, "scale", 1.0) or 1.0,
                threshold=item.threshold,
                invert=item.invert,
            )
            params.image_items.append(ip)
        
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
    
    def on_model_generated(self, keycap_model, text_model, image_inlay=None):
        """模型生成完成"""
        self.current_keycap_model = keycap_model
        self.current_text_model = text_model
        self.current_image_inlay = image_inlay
        
        # 记录生成时的文字位置，用于后续实时预览
        params = self.gen_thread.params
        self.last_generated_text_pos = (params.text_offset_x, params.text_offset_y)
        
        # 更新预览
        self.preview_widget.update_model(keycap_model, text_model, image_inlay)
        
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
        self.current_image_inlay = None
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
            keycap_success, text_success, inlay_success = export_stl_keycap_text(
                self.current_keycap_model,
                self.current_text_model,
                base_path,
                self.current_image_inlay
            )
            
            if keycap_success:
                fname = os.path.basename(base_path)
                msg = f"按键模型已导出: {fname}_keycap.stl"
                
                if text_success:
                    msg += f"\n文字模型已导出: {fname}_text.stl"
                if inlay_success:
                    msg += f"\n图片镶嵌体已导出: {fname}_inlay.stl"
                if text_success or inlay_success:
                    msg += "\n\n【多色打印提示】\n请将相关文件同时拖入切片软件（如选择“作为单一对象加载”），以进行多色打印设置。"
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
            keycap_success, text_success, inlay_success = export_step_keycap_text(
                self.current_keycap_model,
                self.current_text_model,
                base_path,
                self.current_image_inlay
            )
            
            if keycap_success:
                fname = os.path.basename(base_path)
                msg = f"按键模型已导出: {fname}_keycap.step"
                
                if text_success:
                    msg += f"\n文字模型已导出: {fname}_text.step"
                if inlay_success:
                    msg += f"\n图片镶嵌体已导出: {fname}_inlay.step"
                if text_success or inlay_success:
                    msg += "\n\nSTEP文件也已拆分为独立文件以便于CAD处理。"
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
                file_path,
                self.current_image_inlay
            )
            
            if success:
                fname = os.path.basename(file_path)
                msg = f"3MF文件已导出: {fname}\n\n"
                msg += "【多色打印优势】\n"
                msg += "✓ 单个文件包含按键、文字"
                if self.current_image_inlay is not None:
                    msg += "、图片镶嵌体"
                msg += "等部件\n"
                msg += "✓ 自动保留颜色信息（按键=深灰，文字=白色"
                if self.current_image_inlay is not None:
                    msg += "，镶嵌体=金/黄"
                msg += "）\n"
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
