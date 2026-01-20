"""
2D预览组件
显示按键轮廓和字符位置
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QCheckBox, QDoubleSpinBox
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QFontDatabase
from typing import List, Dict, Optional
from core.keycap_presets import PRESET_POSITIONS, u_to_mm
from math import tan, radians
from utils.file_utils import get_font_name


class TextItem:
    """文字项"""
    def __init__(self, text: str, x: float, y: float, font_size: float = 3.0):
        self.text = text
        self.x = x  # 相对于按键中心的偏移（mm）
        self.y = y
        self.font_size = font_size
        self.selected = False


class Preview2DWidget(QWidget):
    """2D预览组件"""
    
    # 信号：文字位置改变
    text_position_changed = pyqtSignal(int, float, float)  # (index, x, y)
    # 信号：文字选中改变 (index)
    selection_changed = pyqtSignal(int)
    # 信号：拖动结束 (用于自动更新)
    drag_finished = pyqtSignal()
    
    # 信号：内容改变 (用于自动更新)
    content_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_width = 18.0  # mm
        self.key_height = 18.0  # mm
        self.key_depth = 8.0     # 新增：键帽高度
        self.side_angle = 0.0    # 新增：侧面斜角
        self.top_thickness = 1.0 # 新增：顶面厚度
        
        self.text_items: List[TextItem] = []
        self.selected_index = -1
        self.drag_start_pos = None        # 鼠标拖动起始位置 (QPoint)
        self.drag_original_pos = None     # 文字拖动前的原始位置 (x, y)
        self.is_dragging_move = False     # 是否发生了拖动移动
        
        self.snap_grid_size = 1.0  # mm 对齐网格大小
        self.snap_enabled = True  # 是否启用对齐
        self.current_font_family = "" # 当前使用的字体族
        self._font_cache = {}    # 字体缓存
        self.setup_ui()
        self.setMinimumSize(300, 300)

    def set_font(self, font_path: str):
        """设置预览字体"""
        if not font_path:
            return
            
        # 简单缓存避免重复加载
        if font_path in self._font_cache:
            self.current_font_family = self._font_cache[font_path]
            self.update()
            return
            
        try:
            # 加载字体文件
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    family = families[0]
                    self.current_font_family = family
                    self._font_cache[font_path] = family
                    self.update()
                    return
            
            # Fallback: 如果加载失败（可能是系统字体），尝试直接读取名称
            family = get_font_name(font_path)
            self.current_font_family = family
            self._font_cache[font_path] = family
            self.update()
            
        except Exception as e:
            print(f"加载预览字体出错: {e}")

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题 (可选，或者也移除？用户没说。保留标题作为指示)
        title = QLabel("2D预览")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addStretch()

    def set_snap_enabled(self, enabled: bool):
        self.snap_enabled = enabled
        self.update()

    def set_snap_grid_size(self, size: float):
        self.snap_grid_size = size
        self.update()
    
    def set_key_size(self, width: float, height: float):
        """设置按键尺寸（mm）"""
        self.key_width = width
        self.key_height = height
        self.update()
        
    def set_key_geometry(self, depth: float, side_angle: float):
        """设置键帽几何参数"""
        self.key_depth = depth
        self.side_angle = side_angle
        self.update()

    def get_top_surface_size(self):
        """计算顶面尺寸"""
        # 顶面宽度 = 底宽 - 2 * 高度 * tan(斜角) (高度是从Z=0到最底部的距离? NO)
        # 这里的 key_depth 是键帽总高度 (excluding stem usually?)
        # Let's assume key_depth is the height of the main body
        # Based on ParameterPanel, key_depth often refers to total depth.
        # But Side Angle usually affects how much it shrinks.
        delta = 2 * self.key_depth * tan(radians(self.side_angle))
        top_w = max(1.0, self.key_width - delta)
        top_h = max(1.0, self.key_height - delta)
        return top_w, top_h
    
    def add_text(self, text: str, font_size: float = 3.0) -> int:
        """添加文字，返回索引"""
        item = TextItem(text, 0.0, 0.0, font_size)
        self.text_items.append(item)
        self.update()
        return len(self.text_items) - 1
    
    def remove_text(self, index: int):
        """移除文字"""
        if 0 <= index < len(self.text_items):
            self.text_items.pop(index)
            if self.selected_index == index:
                self.selected_index = -1
            elif self.selected_index > index:
                self.selected_index -= 1
            self.update()
            
            self.content_changed.emit()
    
    def apply_preset_position(self, position_name: str):
        """应用预设位置"""
        if self.selected_index < 0 or self.selected_index >= len(self.text_items):
            return
        
        # 计算预设位置（相对于按键中心）
        w = self.key_width
        h = self.key_height
        
        positions = {
            "左上": (-w * 0.3, -h * 0.3),
            "中上": (0, -h * 0.3),
            "右上": (w * 0.3, -h * 0.3),
            "左中": (-w * 0.3, 0),
            "中间": (0, 0),
            "右中": (w * 0.3, 0),
            "左下": (-w * 0.3, h * 0.3),
            "中下": (0, h * 0.3),
            "右下": (w * 0.3, h * 0.3),
        }
        
        if position_name in positions:
            x, y = positions[position_name]
            self.text_items[self.selected_index].x = x
            self.text_items[self.selected_index].y = y
            self.update()
            self.text_position_changed.emit(
                self.selected_index, x, y
            )
    
    def get_coordinate_params(self):
        """计算坐标转换参数"""
        margin = 20
        widget_width = self.width() - 2 * margin
        widget_height = self.height() - 2 * margin
        
        # 避免除以零
        if self.key_width <= 0 or self.key_height <= 0:
            return 1.0, self.width()/2, self.height()/2
            
        scale_x = widget_width / self.key_width
        scale_y = widget_height / self.key_height
        scale = min(scale_x, scale_y) * 0.9
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        return scale, center_x, center_y

    def map_to_screen(self, logical_x, logical_y, scale, center_x, center_y):
        """逻辑坐标映射到屏幕坐标"""
        screen_x = center_x + logical_x * scale
        screen_y = center_y - logical_y * scale  # Y轴反转
        return screen_x, screen_y

    def map_from_screen(self, screen_x, screen_y, scale, center_x, center_y):
        """屏幕坐标映射到逻辑坐标"""
        logical_x = (screen_x - center_x) / scale
        logical_y = -(screen_y - center_y) / scale  # Y轴反转
        return logical_x, logical_y

    def get_text_rect(self, item, scale, center_x, center_y):
        """获取文字的屏幕边界框"""
        screen_x, screen_y = self.map_to_screen(item.x, item.y, scale, center_x, center_y)
        
        font = QFont()
        if self.current_font_family:
            font.setFamily(self.current_font_family)
        font.setPointSizeF(item.font_size * scale)
        fm = QFontMetrics(font)
        
        # 计算文字大小
        rect = fm.boundingRect(item.text)
        text_w = rect.width()
        text_h = rect.height()
        
        # 我们希望 (item.x, item.y) 是文字的中心
        # drawText 的位置是基线起点
        # 这里我们需要计算出绘制的起点，以及返回整体的边界框用于点击检测
        
        # 简单的近似：使得文字矩形中心在 (screen_x, screen_y)
        top_left_x = screen_x - text_w / 2
        top_left_y = screen_y - text_h / 2
        
        # 返回屏幕坐标系下的矩形
        return QRectF(top_left_x, top_left_y, text_w, text_h)

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        scale, center_x, center_y = self.get_coordinate_params()
        
        # 绘制按键底面轮廓（灰色）
        key_screen_w = self.key_width * scale
        key_screen_h = self.key_height * scale
        
        key_rect = QRectF(
            center_x - key_screen_w / 2,
            center_y - key_screen_h / 2,
            key_screen_w,
            key_screen_h
        )
        
        painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
        painter.setBrush(QBrush(QColor(245, 245, 245)))
        painter.drawRect(key_rect)
        
        # 绘制顶面轮廓（实线，实际操作区）
        top_w, top_h = self.get_top_surface_size()
        top_screen_w = top_w * scale
        top_screen_h = top_h * scale
        
        top_rect = QRectF(
            center_x - top_screen_w / 2,
            center_y - top_screen_h / 2,
            top_screen_w,
            top_screen_h
        )
        
        # 使用稍深一点的颜色表示顶面
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(top_rect)
        
        # 绘制9宫格参考线（基于顶面）
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        
        # 垂直线
        v_lines = [-top_w/6, top_w/6]
        for lx in v_lines:
            sx, _ = self.map_to_screen(lx, 0, scale, center_x, center_y)
            painter.drawLine(int(sx), int(top_rect.top()), int(sx), int(top_rect.bottom()))
            
        # 水平线
        h_lines = [-top_h/6, top_h/6]
        for ly in h_lines:
            _, sy = self.map_to_screen(0, ly, scale, center_x, center_y)
            painter.drawLine(int(top_rect.left()), int(sy), int(top_rect.right()), int(sy))
        
        # 绘制文字
        for i, item in enumerate(self.text_items):
            # 获取文字矩形（用于居中计算）
            rect = self.get_text_rect(item, scale, center_x, center_y)
            
            # 设置字体
            font = QFont()
            if self.current_font_family:
                font.setFamily(self.current_font_family)
            font.setPointSizeF(item.font_size * scale)
            painter.setFont(font)
            
            # 绘制颜色
            if item.selected:
                painter.setPen(QPen(QColor(255, 0, 0), 2))
            else:
                painter.setPen(QPen(QColor(0, 0, 0), 1))
            
            # 绘制文字 (居中对齐)
            painter.drawText(rect, Qt.AlignCenter, item.text)
            
            # 绘制选择框
            if item.selected:
                padding = 4
                selection_rect = rect.adjusted(-padding, -padding, padding, padding)
                painter.setPen(QPen(QColor(255, 0, 0), 1, Qt.DashLine))
                painter.setBrush(QBrush(Qt.NoBrush))
                painter.drawRect(selection_rect)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        self.setFocus()
        if event.button() == Qt.LeftButton:
            scale, cx, cy = self.get_coordinate_params()
            
            # 检查每个文字项
            clicked_index = -1
            for i, item in enumerate(self.text_items):
                rect = self.get_text_rect(item, scale, cx, cy)
                # 扩大一点点击区域，方便点击小字
                hit_rect = rect.adjusted(-5, -5, 5, 5)
                
                if hit_rect.contains(event.pos()):
                    clicked_index = i
                    break # 找到顶层的（或者列表第一个匹配的）
            
            if clicked_index >= 0:
                self.selected_index = clicked_index
                for i, item in enumerate(self.text_items):
                    item.selected = (i == clicked_index)
                
                # 开始拖动：记录起始鼠标位置和物体原始位置
                self.drag_start_pos = event.pos()
                self.drag_original_pos = (self.text_items[clicked_index].x, self.text_items[clicked_index].y)
                self.is_dragging_move = False # 重置移动标记
            else:
                # 点击空白处，取消选择
                self.selected_index = -1
                for item in self.text_items:
                    item.selected = False
                self.drag_start_pos = None
                self.drag_original_pos = None
            
            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件（拖动）"""
        if self.selected_index >= 0 and self.drag_start_pos is not None and self.drag_original_pos is not None:
            if event.buttons() & Qt.LeftButton and self.selected_index < len(self.text_items):
                scale, cx, cy = self.get_coordinate_params()
                
                # 计算鼠标移动总偏移 (Current - Start)
                dx_screen = event.x() - self.drag_start_pos.x()
                dy_screen = event.y() - self.drag_start_pos.y()
                
                # 只有当移动距离超过阈值才视为拖动 (防抖)
                if (dx_screen**2 + dy_screen**2) > 9: # 3 pixels
                    self.is_dragging_move = True
                
                # 转换到逻辑距离
                dx_logical = dx_screen / scale
                dy_logical = -dy_screen / scale # Y轴反转
                
                # 基于原始位置计算新位置（不影响下一次计算）
                orig_x, orig_y = self.drag_original_pos
                raw_new_x = orig_x + dx_logical
                raw_new_y = orig_y + dy_logical
                
                # 在这里应用吸附
                if self.snap_enabled and self.snap_grid_size > 0:
                    snapped_x = round(raw_new_x / self.snap_grid_size) * self.snap_grid_size
                    snapped_y = round(raw_new_y / self.snap_grid_size) * self.snap_grid_size
                else:
                    snapped_x = raw_new_x
                    snapped_y = raw_new_y

                item = self.text_items[self.selected_index]
                
                # 获取文字实际逻辑大小
                font = QFont()
                if self.current_font_family:
                    font.setFamily(self.current_font_family)
                font.setPointSizeF(item.font_size * scale)
                fm = QFontMetrics(font)
                rect = fm.boundingRect(item.text)
                
                # 逻辑尺寸
                text_logic_w = rect.width() / scale
                text_logic_h = rect.height() / scale
                
                # 顶面边界 Clamping
                top_w, top_h = self.get_top_surface_size()
                
                limit_x = (top_w - text_logic_w) / 2
                limit_y = (top_h - text_logic_h) / 2
                
                if limit_x < 0: limit_x = 0 # 文字比顶面宽，强制居中
                if limit_y < 0: limit_y = 0
                
                final_x = max(-limit_x, min(limit_x, snapped_x))
                final_y = max(-limit_y, min(limit_y, snapped_y))
                
                item.x = final_x
                item.y = final_y
                
                # 不再重置 drag_start_pos，保持累积
                self.update()
                
                self.text_position_changed.emit(self.selected_index, item.x, item.y)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            if self.drag_start_pos is not None and self.is_dragging_move:
                self.drag_finished.emit()
            self.drag_start_pos = None
            self.drag_original_pos = None
            self.is_dragging_move = False

    def keyPressEvent(self, event):
        """键盘按键事件"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected_index >= 0:
                self.remove_text(self.selected_index)
                
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        scale, cx, cy = self.get_coordinate_params()
        
        clicked_index = -1
        for i, item in enumerate(self.text_items):
            rect = self.get_text_rect(item, scale, cx, cy)
            hit_rect = rect.adjusted(-5, -5, 5, 5)
            if hit_rect.contains(event.pos()):
                clicked_index = i
                break
        
        if clicked_index >= 0:
            self.selected_index = clicked_index
            for i, item in enumerate(self.text_items):
                item.selected = (i == clicked_index)
            self.update()
            
            menu = QMenu(self)
            delete_action = menu.addAction("删除")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            
            if action == delete_action:
                self.remove_text(clicked_index)

    def clear_texts(self):
        """清除所有文字"""
        self.text_items.clear()
        self.selected_index = -1
        self.update()
