"""
2D预览组件
显示按键轮廓、文字和图片位置
"""
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QCheckBox, QDoubleSpinBox
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QFontDatabase, QImage
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


class ImageItem:
    """图片项"""
    def __init__(self, path: str, x: float = 0.0, y: float = 0.0, size: float = 6.0,
                 depth: float = 0.5, threshold: int = 128, invert: bool = False, scale: float = 1.0):
        self.path = path
        self.x = x
        self.y = y
        self.size = size
        self.depth = depth
        self.threshold = threshold
        self.invert = invert
        self.scale = scale
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
        self.image_items: List[ImageItem] = []
        self.selected_index = -1
        self.selected_image_index = -1
        self.drag_start_pos = None        # 鼠标拖动起始位置 (QPoint)
        self.drag_original_pos = None     # 拖动前的原始位置 (x, y)
        self.drag_is_image = False        # 当前拖动的是图片
        self.is_dragging_move = False     # 是否发生了拖动移动
        
        self.snap_grid_size = 1.0  # mm 对齐网格大小
        self.snap_enabled = True  # 是否启用对齐
        self.current_font_family = "" # 当前使用的字体族
        self._font_cache = {}    # 字体缓存
        self._image_cache: Dict[str, QImage] = {}  # 图片缓存 path->QImage
        self.HANDLE_SZ = 10  # 缩放手柄边长（像素）
        self.resizing = None  # None 或 ("image", idx, corner, {dict}) 或 ("text", idx, {dict})
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
            self.selection_changed.emit(self.selected_index)
            self.content_changed.emit()
    
    def add_image(self, path: str, size: float = 6.0, depth: float = 0.5,
                  threshold: int = 128, invert: bool = False, scale: float = 1.0) -> int:
        """添加图片，返回索引。"""
        if not path or not Path(path).is_file():
            return -1
        item = ImageItem(path, 0.0, 0.0, size, depth, threshold, invert, scale)
        self.image_items.append(item)
        self.update()
        self.content_changed.emit()
        return len(self.image_items) - 1
    
    def remove_image(self, index: int):
        """移除图片"""
        if 0 <= index < len(self.image_items):
            self.image_items.pop(index)
            if self.selected_image_index == index:
                self.selected_image_index = -1
            elif self.selected_image_index > index:
                self.selected_image_index -= 1
            self.update()
            self.content_changed.emit()
    
    def clear_images(self):
        """清除所有图片"""
        self.image_items.clear()
        self.selected_image_index = -1
        self.update()
        self.content_changed.emit()
    
    def get_image_rect(self, item: ImageItem, scale: float, center_x: float, center_y: float) -> QRectF:
        """获取图片在屏幕上的绘制矩形（中心在 item.x, item.y，按 item.size*item.scale 为最长边缩放）。"""
        eff = item.size * (getattr(item, "scale", 1.0) or 1.0)
        img = self._load_image(item.path)
        if img is None or img.isNull():
            side = eff * scale
            sx, sy = self.map_to_screen(item.x, item.y, scale, center_x, center_y)
            return QRectF(sx - side/2, sy - side/2, side, side)
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            side = eff * scale
            sx, sy = self.map_to_screen(item.x, item.y, scale, center_x, center_y)
            return QRectF(sx - side/2, sy - side/2, side, side)
        m = max(w, h)
        w_mm = eff * (w / m)
        h_mm = eff * (h / m)
        w_sc = w_mm * scale
        h_sc = h_mm * scale
        sx, sy = self.map_to_screen(item.x, item.y, scale, center_x, center_y)
        return QRectF(sx - w_sc/2, sy - h_sc/2, w_sc, h_sc)
    
    def _load_image(self, path: str) -> Optional[QImage]:
        if not path:
            return None
        if path in self._image_cache:
            return self._image_cache[path]
        img = QImage(path)
        if not img.isNull():
            self._image_cache[path] = img
        return img if not img.isNull() else None
    
    def get_image_size_mm(self, item: ImageItem) -> tuple:
        """返回 (width_mm, height_mm)，已含 scale。"""
        eff = item.size * (getattr(item, "scale", 1.0) or 1.0)
        img = self._load_image(item.path)
        if img is None or img.isNull():
            return (eff, eff)
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return (eff, eff)
        m = max(w, h)
        return (eff * (w / m), eff * (h / m))
    
    def _handle_rect_at_corner(self, rect: QRectF, corner: int) -> QRectF:
        """corner: 0=topLeft, 1=topRight, 2=bottomRight, 3=bottomLeft。返回以该角为中心的手柄矩形。"""
        if corner == 0:
            cx, cy = rect.left(), rect.top()
        elif corner == 1:
            cx, cy = rect.right(), rect.top()
        elif corner == 2:
            cx, cy = rect.right(), rect.bottom()
        else:
            cx, cy = rect.left(), rect.bottom()
        h = self.HANDLE_SZ / 2
        return QRectF(cx - h, cy - h, self.HANDLE_SZ, self.HANDLE_SZ)
    
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
            
            # 绘制选择框与缩放手柄（PS 式：拖动角点缩放）
            if item.selected:
                padding = 4
                selection_rect = rect.adjusted(-padding, -padding, padding, padding)
                painter.setPen(QPen(QColor(255, 0, 0), 1, Qt.DashLine))
                painter.setBrush(QBrush(Qt.NoBrush))
                painter.drawRect(selection_rect)
                painter.setPen(QPen(QColor(255, 0, 0), 1))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                hr = self._handle_rect_at_corner(rect, 2)
                painter.drawRect(hr)
        
        # 绘制图片
        for i, img_item in enumerate(self.image_items):
            rect = self.get_image_rect(img_item, scale, center_x, center_y)
            qimg = self._load_image(img_item.path)
            if qimg is not None and not qimg.isNull():
                painter.drawImage(rect, qimg)
            else:
                painter.setPen(QPen(QColor(120, 120, 120), 1))
                painter.setBrush(QBrush(QColor(240, 240, 240)))
                painter.drawRect(rect)
                painter.setPen(QPen(QColor(80, 80, 80), 1))
                painter.drawText(rect, Qt.AlignCenter, "?")
            if img_item.selected:
                padding = 4
                sel = rect.adjusted(-padding, -padding, padding, padding)
                painter.setPen(QPen(QColor(255, 0, 0), 1, Qt.DashLine))
                painter.setBrush(QBrush(Qt.NoBrush))
                painter.drawRect(sel)
                painter.setPen(QPen(QColor(255, 0, 0), 1))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                for c in range(4):
                    painter.drawRect(self._handle_rect_at_corner(rect, c))
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        self.setFocus()
        if event.button() == Qt.LeftButton:
            scale, cx, cy = self.get_coordinate_params()
            
            # 1) 优先检查缩放手柄（PS 式：拖动角点缩放）
            if self.selected_image_index >= 0 and self.selected_image_index < len(self.image_items):
                it = self.image_items[self.selected_image_index]
                rect = self.get_image_rect(it, scale, cx, cy)
                for corner in range(4):
                    if self._handle_rect_at_corner(rect, corner).contains(event.pos()):
                        w_mm, h_mm = self.get_image_size_mm(it)
                        if corner == 0:
                            fx, fy = it.x + w_mm/2, it.y - h_mm/2
                        elif corner == 1:
                            fx, fy = it.x - w_mm/2, it.y - h_mm/2
                        elif corner == 2:
                            fx, fy = it.x - w_mm/2, it.y + h_mm/2
                        else:
                            fx, fy = it.x + w_mm/2, it.y + h_mm/2
                        self.resizing = ("image", self.selected_image_index, corner, {"fx": fx, "fy": fy, "orig_w": w_mm, "orig_h": h_mm})
                        self.drag_start_pos = None
                        self.drag_original_pos = None
                        self.update()
                        return
            if self.selected_index >= 0 and self.selected_index < len(self.text_items):
                it = self.text_items[self.selected_index]
                rect = self.get_text_rect(it, scale, cx, cy)
                if self._handle_rect_at_corner(rect, 2).contains(event.pos()):
                    ow, oh = rect.width() / scale, rect.height() / scale
                    fx, fy = it.x - ow/2, it.y + oh/2
                    self.resizing = ("text", self.selected_index, {"fx": fx, "fy": fy, "orig_fs": it.font_size, "orig_w": ow, "orig_h": oh})
                    self.drag_start_pos = None
                    self.drag_original_pos = None
                    self.update()
                    return
            
            # 2) 检查图片/文字本体（选中、移动）
            clicked_image = -1
            for i, item in enumerate(self.image_items):
                rect = self.get_image_rect(item, scale, cx, cy)
                if rect.adjusted(-5, -5, 5, 5).contains(event.pos()):
                    clicked_image = i
                    break
            
            if clicked_image >= 0:
                self.selected_image_index = clicked_image
                self.selected_index = -1
                for t in self.text_items:
                    t.selected = False
                for j, img in enumerate(self.image_items):
                    img.selected = (j == clicked_image)
                self.drag_start_pos = event.pos()
                it = self.image_items[clicked_image]
                self.drag_original_pos = (it.x, it.y)
                self.drag_is_image = True
                self.is_dragging_move = False
                self.selection_changed.emit(-1)
                self.update()
                return
            
            # 检查文字项
            clicked_index = -1
            for i, item in enumerate(self.text_items):
                rect = self.get_text_rect(item, scale, cx, cy)
                hit_rect = rect.adjusted(-5, -5, 5, 5)
                if hit_rect.contains(event.pos()):
                    clicked_index = i
                    break
            
            if clicked_index >= 0:
                self.selected_index = clicked_index
                self.selected_image_index = -1
                for i, item in enumerate(self.text_items):
                    item.selected = (i == clicked_index)
                for img in self.image_items:
                    img.selected = False
                self.drag_start_pos = event.pos()
                self.drag_original_pos = (self.text_items[clicked_index].x, self.text_items[clicked_index].y)
                self.drag_is_image = False
                self.is_dragging_move = False
                self.selection_changed.emit(clicked_index)
            else:
                self.selected_index = -1
                self.selected_image_index = -1
                for item in self.text_items:
                    item.selected = False
                for img in self.image_items:
                    img.selected = False
                self.drag_start_pos = None
                self.drag_original_pos = None
                self.drag_is_image = False
                self.selection_changed.emit(-1)
            
            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件（拖动）"""
        # 1) 优先处理 PS 式拖动手柄缩放
        if (event.buttons() & Qt.LeftButton) and self.resizing is not None:
            scale, cx, cy = self.get_coordinate_params()
            lx, ly = self.map_from_screen(event.x(), event.y(), scale, cx, cy)
            if self.resizing[0] == "image":
                _, idx, corner, d = self.resizing
                if idx < 0 or idx >= len(self.image_items):
                    self.resizing = None
                    return
                item = self.image_items[idx]
                fx, fy = d["fx"], d["fy"]
                if corner == 0:
                    new_w, new_h = abs(d["fx"] - lx), abs(ly - d["fy"])
                elif corner == 1:
                    new_w, new_h = abs(lx - d["fx"]), abs(ly - d["fy"])
                elif corner == 2:
                    new_w, new_h = abs(lx - d["fx"]), abs(d["fy"] - ly)
                else:
                    new_w, new_h = abs(d["fx"] - lx), abs(d["fy"] - ly)
                new_size = max(new_w, new_h)
                new_size = max(0.5, min(30.0, new_size))
                mo = max(d["orig_w"], d["orig_h"])
                if mo <= 0:
                    mo = 1.0
                new_w_mm = new_size * (d["orig_w"] / mo)
                new_h_mm = new_size * (d["orig_h"] / mo)
                item.x = (lx + fx) / 2
                item.y = (ly + fy) / 2
                item.size = new_size
                item.scale = 1.0
                self.update()
                self.content_changed.emit()
            else:  # "text"
                _, idx, d = self.resizing
                if idx < 0 or idx >= len(self.text_items):
                    self.resizing = None
                    return
                item = self.text_items[idx]
                fx, fy = d["fx"], d["fy"]
                new_h = d["fy"] - ly
                new_font_size = d["orig_fs"] * (new_h / d["orig_h"]) if d.get("orig_h") else d["orig_fs"]
                new_font_size = max(0.5, min(20.0, new_font_size))
                new_w = d["orig_w"] * (new_font_size / d["orig_fs"]) if d.get("orig_fs") else d["orig_w"]
                item.font_size = new_font_size
                item.x = fx + new_w / 2
                item.y = (fy + ly) / 2
                self.update()
                self.content_changed.emit()
                self.text_position_changed.emit(idx, item.x, item.y)
            return

        if not (event.buttons() & Qt.LeftButton) or self.drag_start_pos is None or self.drag_original_pos is None:
            return

        scale, cx, cy = self.get_coordinate_params()
        dx_screen = event.x() - self.drag_start_pos.x()
        dy_screen = event.y() - self.drag_start_pos.y()
        if (dx_screen**2 + dy_screen**2) > 9:
            self.is_dragging_move = True
        dx_logical = dx_screen / scale
        dy_logical = -dy_screen / scale
        orig_x, orig_y = self.drag_original_pos
        raw_new_x = orig_x + dx_logical
        raw_new_y = orig_y + dy_logical
        if self.snap_enabled and self.snap_grid_size > 0:
            snapped_x = round(raw_new_x / self.snap_grid_size) * self.snap_grid_size
            snapped_y = round(raw_new_y / self.snap_grid_size) * self.snap_grid_size
        else:
            snapped_x, snapped_y = raw_new_x, raw_new_y
        top_w, top_h = self.get_top_surface_size()
        
        if self.drag_is_image and self.selected_image_index >= 0 and self.selected_image_index < len(self.image_items):
            item = self.image_items[self.selected_image_index]
            w_mm, h_mm = self.get_image_size_mm(item)
            limit_x = max(0, (top_w - w_mm) / 2)
            limit_y = max(0, (top_h - h_mm) / 2)
            item.x = max(-limit_x, min(limit_x, snapped_x))
            item.y = max(-limit_y, min(limit_y, snapped_y))
            self.update()
            return
        
        if self.selected_index >= 0 and self.selected_index < len(self.text_items):
            item = self.text_items[self.selected_index]
            font = QFont()
            if self.current_font_family:
                font.setFamily(self.current_font_family)
            font.setPointSizeF(item.font_size * scale)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(item.text)
            text_logic_w = rect.width() / scale
            text_logic_h = rect.height() / scale
            limit_x = max(0, (top_w - text_logic_w) / 2)
            limit_y = max(0, (top_h - text_logic_h) / 2)
            item.x = max(-limit_x, min(limit_x, snapped_x))
            item.y = max(-limit_y, min(limit_y, snapped_y))
            self.update()
            self.text_position_changed.emit(self.selected_index, item.x, item.y)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            if self.resizing is not None:
                self.drag_finished.emit()
                self.resizing = None
            if self.drag_start_pos is not None and self.is_dragging_move:
                self.drag_finished.emit()
            self.drag_start_pos = None
            self.drag_original_pos = None
            self.is_dragging_move = False

    def keyPressEvent(self, event):
        """键盘按键事件"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected_image_index >= 0:
                self.remove_image(self.selected_image_index)
            elif self.selected_index >= 0:
                self.remove_text(self.selected_index)
                
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        scale, cx, cy = self.get_coordinate_params()
        
        clicked_image = -1
        for i, item in enumerate(self.image_items):
            rect = self.get_image_rect(item, scale, cx, cy)
            if rect.adjusted(-5, -5, 5, 5).contains(event.pos()):
                clicked_image = i
                break
        
        if clicked_image >= 0:
            self.selected_image_index = clicked_image
            self.selected_index = -1
            for t in self.text_items:
                t.selected = False
            for j, img in enumerate(self.image_items):
                img.selected = (j == clicked_image)
            self.selection_changed.emit(-1)
            self.update()
            menu = QMenu(self)
            delete_action = menu.addAction("删除")
            if menu.exec_(self.mapToGlobal(event.pos())) == delete_action:
                self.remove_image(clicked_image)
            return
        
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
            self.selection_changed.emit(clicked_index)
            self.update()
            menu = QMenu(self)
            delete_action = menu.addAction("删除")
            if menu.exec_(self.mapToGlobal(event.pos())) == delete_action:
                self.remove_text(clicked_index)

    def clear_texts(self):
        """清除所有文字与图片"""
        self.text_items.clear()
        self.image_items.clear()
        self.selected_index = -1
        self.selected_image_index = -1
        self.selection_changed.emit(-1)
        self.update()
