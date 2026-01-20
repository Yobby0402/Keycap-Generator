"""
主窗口
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
                             QStatusBar, QProgressBar, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
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
import cadquery as cq


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
        self.settings = Settings()
        self.setup_ui()
        self.setup_menu()
        self.setup_statusbar()
        self.load_settings()
    
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
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
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
        
        # 确保字体路径已设置（如果选择了字体）
        if params.font_path is None and self.parameter_panel.font_combo.currentIndex() >= 0:
            font_path = self.parameter_panel.font_combo.currentData()
            if font_path:
                params.font_path = font_path
    
    def on_insert_text(self, text: str, font_size: float):
        """插入文字到2D预览"""
        index = self.preview_2d_widget.add_text(text, font_size)
        # 更新参数中的文字
        self.parameter_panel.params.letter = text
        self.parameter_panel.params.text_height = font_size
    
    def on_text_position_changed(self, index: int, x: float, y: float):
        """文字位置改变"""
        # 更新参数中的文字偏移
        if index < len(self.preview_2d_widget.text_items):
            item = self.preview_2d_widget.text_items[index]
            self.parameter_panel.params.text_offset_x = item.x
            self.parameter_panel.params.text_offset_y = item.y
            self.parameter_panel.params.letter = item.text
            self.parameter_panel.params.text_height = item.font_size
    
    def generate_model(self):
        """生成模型"""
        params = self.parameter_panel.get_parameters()
        
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
        self.current_keycap_model = None
        self.current_text_model = None
        
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
                self.status_bar.showMessage(f"已导出: {base_path}_keycap.stl")
                if text_success:
                    self.status_bar.showMessage(
                        f"已导出: {base_path}_keycap.stl 和 {base_path}_text.stl"
                    )
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
                self.status_bar.showMessage(f"已导出: {base_path}_keycap.step")
                if text_success:
                    self.status_bar.showMessage(
                        f"已导出: {base_path}_keycap.step 和 {base_path}_text.step"
                    )
            else:
                QMessageBox.warning(self, "导出失败", "无法导出STEP文件。")
    
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新2D预览的对齐设置
            self.preview_2d_widget.snap_enabled = self.settings.get_snap_enabled()
            self.preview_2d_widget.snap_grid_size = self.settings.get_snap_grid_size()
            # 更新UI控件
            self.preview_2d_widget.snap_checkbox.setChecked(self.settings.get_snap_enabled())
            self.preview_2d_widget.snap_spin.setValue(self.settings.get_snap_grid_size())
    
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
