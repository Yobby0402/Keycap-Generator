"""
主窗口
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                             QStatusBar, QProgressBar, QDialog, QActionGroup)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
from ui.parameter_panel import ParameterPanel
from ui.preview_widget import PreviewWidget
from ui.preview_2d_widget import Preview2DWidget
from ui.settings_dialog import SettingsDialog
from core.parameters import KeycapParameters
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
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("机械键盘按键模型生成器")
        self.setMinimumSize(1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局（水平分割：左侧参数，右侧预览）
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 参数面板（左侧）
        self.parameter_panel = ParameterPanel()
        self.parameter_panel.parameters_changed.connect(self.on_parameters_changed)
        self.parameter_panel.generate_btn.clicked.connect(self.generate_model)
        self.parameter_panel.insert_text_signal.connect(self.on_insert_text)  # 连接插入文字信号
        main_layout.addWidget(self.parameter_panel, stretch=1)
        
        # 右侧预览区域（垂直分割：上方2D，下方3D）
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(5)
        
        # 2D预览（上方）
        self.preview_2d_widget = Preview2DWidget()
        self.preview_2d_widget.text_position_changed.connect(self.on_text_position_changed)
        self.preview_2d_widget.drag_finished.connect(self.check_auto_update)
        self.preview_2d_widget.content_changed.connect(self.check_auto_update)
        # 从设置加载对齐配置
        self.preview_2d_widget.snap_enabled = self.settings.get_snap_enabled()
        self.preview_2d_widget.snap_grid_size = self.settings.get_snap_grid_size()
        preview_layout.addWidget(self.preview_2d_widget, stretch=1)
        
        # 3D预览窗口（下方）
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget, stretch=2)
        
        # 右侧容器
        preview_container = QWidget()
        preview_container.setLayout(preview_layout)
        main_layout.addWidget(preview_container, stretch=2)
    
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
        
        # 从2D预览同步所有文字项到参数
        # 这解决了多文字生成问题，并确保位置与预览完全一致
        params.text_items = []
        for item in self.preview_2d_widget.text_items:
            params.text_items.append({
                'text': item.text,
                'x': item.x,
                'y': item.y,
                'size': item.font_size
            })
        
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
        self.parameter_panel.top_angle_spin.setValue(0.0)
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
        # 可以在这里添加保存提示等
        event.accept()
