"""
2D预览组件
显示按键轮廓和字符位置
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from typing import List, Dict, Optional
from core.keycap_presets import PRESET_POSITIONS, u_to_mm


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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_width = 18.0  # mm
        self.key_height = 18.0  # mm
        self.text_items: List[TextItem] = []
        self.selected_index = -1
        self.drag_start_pos = None
        self.snap_grid_size = 1.0  # mm 对齐网格大小
        self.snap_enabled = True  # 是否启用对齐
        self.setup_ui()
        self.setMinimumSize(300, 300)
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("2D预览")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 预设位置按钮
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("预设位置:"))
        
        positions = ["左上", "中上", "右上", "左中", "中间", "右中", "左下", "中下", "右下"]
        for pos in positions:
            btn = QPushButton(pos)
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda checked, p=pos: self.apply_preset_position(p))
            preset_layout.addWidget(btn)
        
        layout.addLayout(preset_layout)
    
    def set_key_size(self, width: float, height: float):
        """设置按键尺寸（mm）"""
        self.key_width = width
        self.key_height = height
        self.update()
    
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
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算绘制区域
        margin = 20
        widget_width = self.width() - 2 * margin
        widget_height = self.height() - 2 * margin
        
        # 计算缩放比例（保持宽高比）
        scale_x = widget_width / self.key_width if self.key_width > 0 else 1
        scale_y = widget_height / self.key_height if self.key_height > 0 else 1
        scale = min(scale_x, scale_y) * 0.9  # 留一些边距
        
        # 计算中心点
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # 绘制按键轮廓
        key_rect = QRectF(
            center_x - (self.key_width * scale) / 2,
            center_y - (self.key_height * scale) / 2,
            self.key_width * scale,
            self.key_height * scale
        )
        
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRect(key_rect)
        
        # 绘制9宫格参考线
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        # 垂直线
        painter.drawLine(
            int(center_x - (self.key_width * scale) / 3),
            int(center_y - (self.key_height * scale) / 2),
            int(center_x - (self.key_width * scale) / 3),
            int(center_y + (self.key_height * scale) / 2)
        )
        painter.drawLine(
            int(center_x + (self.key_width * scale) / 3),
            int(center_y - (self.key_height * scale) / 2),
            int(center_x + (self.key_width * scale) / 3),
            int(center_y + (self.key_height * scale) / 2)
        )
        # 水平线
        painter.drawLine(
            int(center_x - (self.key_width * scale) / 2),
            int(center_y - (self.key_height * scale) / 3),
            int(center_x + (self.key_width * scale) / 2),
            int(center_y - (self.key_height * scale) / 3)
        )
        painter.drawLine(
            int(center_x - (self.key_width * scale) / 2),
            int(center_y + (self.key_height * scale) / 3),
            int(center_x + (self.key_width * scale) / 2),
            int(center_y + (self.key_height * scale) / 3)
        )
        
        # 绘制文字
        for i, item in enumerate(self.text_items):
            # 计算文字位置（相对于中心）
            # 注意：Y轴需要反转（2D预览Y向下，3D预览Y向上）
            text_x = center_x + item.x * scale
            text_y = center_y - item.y * scale  # Y轴反转
            
            # 设置字体
            font = QFont()
            font.setPointSizeF(item.font_size * scale)
            painter.setFont(font)
            
            # 绘制文字
            if item.selected:
                painter.setPen(QPen(QColor(255, 0, 0), 2))
            else:
                painter.setPen(QPen(QColor(0, 0, 0), 1))
            
            painter.drawText(
                int(text_x),
                int(text_y),
                item.text
            )
            
            # 绘制选择框
            if item.selected:
                fm = QFontMetrics(font)
                text_rect = fm.boundingRect(item.text)
                selection_rect = QRectF(
                    text_x - 5,
                    text_y - text_rect.height() - 5,
                    text_rect.width() + 10,
                    text_rect.height() + 10
                )
                painter.setPen(QPen(QColor(255, 0, 0), 1, Qt.DashLine))
                painter.setBrush(QBrush(Qt.NoBrush))
                painter.drawRect(selection_rect)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击了文字
            margin = 20
            widget_width = self.width() - 2 * margin
            widget_height = self.height() - 2 * margin
            
            scale_x = widget_width / self.key_width if self.key_width > 0 else 1
            scale_y = widget_height / self.key_height if self.key_height > 0 else 1
            scale = min(scale_x, scale_y) * 0.9
            
            center_x = self.width() / 2
            center_y = self.height() / 2
            
            # 检查每个文字项
            for i, item in enumerate(self.text_items):
                text_x = center_x + item.x * scale
                text_y = center_y - item.y * scale  # Y轴反转
                
                # 简单的点击检测（可以根据实际文字大小调整）
                if abs(event.x() - text_x) < 20 and abs(event.y() - text_y) < 20:
                    self.selected_index = i
                    item.selected = True
                    self.drag_start_pos = event.pos()
                    self.update()
                    return
            
            # 如果没有点击到文字，取消选择
            for item in self.text_items:
                item.selected = False
            self.selected_index = -1
            self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件（拖动）"""
        if self.selected_index >= 0 and self.drag_start_pos is not None:
            if event.buttons() & Qt.LeftButton and self.selected_index < len(self.text_items):
                # 计算偏移
                margin = 20
                widget_width = self.width() - 2 * margin
                widget_height = self.height() - 2 * margin
                
                scale_x = widget_width / self.key_width if self.key_width > 0 else 1
                scale_y = widget_height / self.key_height if self.key_height > 0 else 1
                scale = min(scale_x, scale_y) * 0.9
                
                dx = (event.x() - self.drag_start_pos.x()) / scale
                dy = -(event.y() - self.drag_start_pos.y()) / scale  # Y轴反转
                
                item = self.text_items[self.selected_index]
                new_x = item.x + dx
                new_y = item.y + dy
                
                # 限位：限制在按键范围内
                w_half = self.key_width / 2
                h_half = self.key_height / 2
                new_x = max(-w_half, min(w_half, new_x))
                new_y = max(-h_half, min(h_half, new_y))
                
                # 对齐吸附
                if self.snap_enabled and self.snap_grid_size > 0:
                    new_x = round(new_x / self.snap_grid_size) * self.snap_grid_size
                    new_y = round(new_y / self.snap_grid_size) * self.snap_grid_size
                    # 再次限位（对齐后可能超出范围）
                    new_x = max(-w_half, min(w_half, new_x))
                    new_y = max(-h_half, min(h_half, new_y))
                
                item.x = new_x
                item.y = new_y
                
                # 更新拖动起始位置（使用当前位置，而不是事件位置）
                # 这样可以累积拖动距离
                self.drag_start_pos = event.pos()
                self.update()
                
                # 发出信号
                self.text_position_changed.emit(
                    self.selected_index, item.x, item.y
                )
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = None
    
    def get_text_positions(self) -> List[tuple]:
        """获取所有文字位置"""
        return [(item.x, item.y) for item in self.text_items]
    
    def on_snap_changed(self, state):
        """对齐开关改变"""
        self.snap_enabled = state == Qt.Checked
    
    def on_snap_size_changed(self, value):
        """对齐网格大小改变"""
        self.snap_grid_size = value
    
    def clear_texts(self):
        """清除所有文字"""
        self.text_items.clear()
        self.selected_index = -1
        self.update()
