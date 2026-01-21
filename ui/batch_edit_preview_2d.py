"""
批量编辑2D预览组件
显示按键轮廓，字符用"X"代替，支持拖动调整
"""
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from core.key_type_analyzer import KeyTypeSignature
from core.batch_edit_config import BatchEditConfig
from core.legend_mapping import _calculate_base_position
from core.keycap_presets import u_to_mm
from typing import Optional


class TextItem:
    """文字项（用于拖动）"""
    def __init__(self, text: str, x: float, y: float, font_size: float, pos_idx: int):
        self.text = text
        self.x = x  # 相对于按键中心的偏移（mm）
        self.y = y
        self.font_size = font_size
        self.pos_idx = pos_idx  # KLE位置索引
        self.selected = False


class BatchEditPreview2D(QWidget):
    """批量编辑2D预览（字符用X代替，支持拖动）"""
    
    # 信号：位置改变
    position_changed = pyqtSignal(int, float, float)  # (pos_idx, offset_x, offset_y)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_type: Optional[KeyTypeSignature] = None
        self.config: Optional[BatchEditConfig] = None
        self.text_items = []  # List[TextItem]
        self.selected_index = -1
        self.drag_start_pos = None
        self.drag_original_pos = None
        self.is_dragging_move = False
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        title = QLabel("2D预览（字符用X代替）")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addStretch()
    
    def update_preview(self, key_type: KeyTypeSignature, config: BatchEditConfig):
        """更新预览"""
        self.key_type = key_type
        self.config = config
        
        # 重建text_items
        self.text_items = []
        if key_type and config:
            key_width_mm = u_to_mm(key_type.width)
            key_height_mm = u_to_mm(key_type.height)
            
            for pos_idx in sorted(key_type.label_positions):
                style = config.get_style_for_position(pos_idx)
                base_x, base_y = _calculate_base_position(pos_idx, key_width_mm, key_height_mm)
                
                # 创建TextItem
                # _calculate_base_position返回的坐标是数学坐标系（Y向上为正）
                # map_to_screen会反转Y轴，所以这里直接使用base_y
                text_item = TextItem(
                    text="X",
                    x=base_x + style.offset_x,
                    y=base_y + style.offset_y,
                    font_size=style.size,
                    pos_idx=pos_idx
                )
                self.text_items.append(text_item)
                
                # 调试信息（仅位置0）
                if pos_idx == 0:
                    print(f"位置0调试:")
                    print(f"  - base_x={base_x:.2f}, base_y={base_y:.2f}")
                    print(f"  - offset_x={style.offset_x:.2f}, offset_y={style.offset_y:.2f}")
                    print(f"  - final_x={text_item.x:.2f}, final_y={text_item.y:.2f}")
                    print(f"  - key_width={key_width_mm:.2f}, key_height={key_height_mm:.2f}")
                    print(f"  - half_w={key_width_mm/2:.2f}, half_h={key_height_mm/2:.2f}")
                    # 验证位置是否在按键范围内
                    half_w = key_width_mm / 2
                    half_h = key_height_mm / 2
                    in_range_x = -half_w <= text_item.x <= half_w
                    in_range_y = -half_h <= text_item.y <= half_h
                    print(f"  - 在范围内: X={in_range_x}, Y={in_range_y}")
                    print(f"  - 范围: X=[{-half_w:.2f}, {half_w:.2f}], Y=[{-half_h:.2f}, {half_h:.2f}]")
        
        self.update()
    
    def get_coordinate_params(self):
        """获取坐标参数（与Preview2DWidget一致）"""
        if not self.key_type:
            return 1.0, self.width() / 2, self.height() / 2
        
        key_width_mm = u_to_mm(self.key_type.width)
        key_height_mm = u_to_mm(self.key_type.height)
        
        # 计算缩放（与Preview2DWidget一致）
        margin = 20
        widget_width = self.width() - 2 * margin
        widget_height = self.height() - 2 * margin  # 与Preview2DWidget一致，不考虑标题
        
        if key_width_mm <= 0 or key_height_mm <= 0:
            return 1.0, self.width() / 2, self.height() / 2
        
        scale_x = widget_width / key_width_mm
        scale_y = widget_height / key_height_mm
        scale = min(scale_x, scale_y) * 0.9
        
        # 中心位置（与Preview2DWidget一致）
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        return scale, center_x, center_y
    
    def map_to_screen(self, logical_x, logical_y, scale, center_x, center_y):
        """逻辑坐标映射到屏幕坐标（与Preview2DWidget一致）"""
        screen_x = center_x + logical_x * scale
        screen_y = center_y - logical_y * scale  # Y轴反转
        return screen_x, screen_y
    
    def map_from_screen(self, screen_x, screen_y, scale, center_x, center_y):
        """屏幕坐标映射到逻辑坐标"""
        logical_x = (screen_x - center_x) / scale
        logical_y = -(screen_y - center_y) / scale  # Y轴反转
        return logical_x, logical_y
    
    def get_text_rect(self, item: TextItem, scale, center_x, center_y):
        """获取文字的屏幕边界框（与Preview2DWidget一致）"""
        screen_x, screen_y = self.map_to_screen(item.x, item.y, scale, center_x, center_y)
        
        font = QFont()
        font.setPointSizeF(item.font_size * scale)
        fm = QFontMetrics(font)
        
        rect = fm.boundingRect(item.text)
        text_w = rect.width()
        text_h = rect.height()
        
        # 文字矩形中心在 (screen_x, screen_y)
        top_left_x = screen_x - text_w / 2
        top_left_y = screen_y - text_h / 2
        
        return QRectF(top_left_x, top_left_y, text_w, text_h)
    
    def paintEvent(self, event):
        """绘制事件（与Preview2DWidget一致）"""
        if self.key_type is None or self.config is None:
            painter = QPainter(self)
            painter.drawText(self.rect(), Qt.AlignCenter, "请选择按键类型")
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        scale, center_x, center_y = self.get_coordinate_params()
        
        key_width_mm = u_to_mm(self.key_type.width)
        key_height_mm = u_to_mm(self.key_type.height)
        
        # 绘制按键底面轮廓（灰色）- 与Preview2DWidget一致
        key_screen_w = key_width_mm * scale
        key_screen_h = key_height_mm * scale
        
        key_rect = QRectF(
            center_x - key_screen_w / 2,
            center_y - key_screen_h / 2,
            key_screen_w,
            key_screen_h
        )
        
        painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
        painter.setBrush(QBrush(QColor(245, 245, 245)))
        painter.drawRect(key_rect)
        
        # 绘制顶面轮廓（实线，实际操作区）- 与Preview2DWidget一致
        # 注意：Preview2DWidget会计算顶面尺寸（考虑斜角），这里简化处理
        top_rect = QRectF(
            center_x - key_screen_w / 2,
            center_y - key_screen_h / 2,
            key_screen_w,
            key_screen_h
        )
        
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.setBrush(QBrush(QColor(230, 230, 230)))
        painter.drawRect(top_rect)
        
        # 绘制9宫格参考线
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DashLine))
        
        # 垂直线
        v_lines = [-key_width_mm/6, key_width_mm/6]
        for lx in v_lines:
            sx, _ = self.map_to_screen(lx, 0, scale, center_x, center_y)
            painter.drawLine(int(sx), int(top_rect.top()), int(sx), int(top_rect.bottom()))
        
        # 水平线
        h_lines = [-key_height_mm/6, key_height_mm/6]
        for ly in h_lines:
            _, sy = self.map_to_screen(0, ly, scale, center_x, center_y)
            painter.drawLine(int(top_rect.left()), int(sy), int(top_rect.right()), int(sy))
        
        # 绘制文字
        for i, item in enumerate(self.text_items):
            rect = self.get_text_rect(item, scale, center_x, center_y)
            
            # 设置字体
            font = QFont()
            font.setPointSizeF(item.font_size * scale)
            painter.setFont(font)
            
            # 绘制颜色
            if item.selected:
                painter.setPen(QPen(QColor(255, 0, 0), 2))
            else:
                painter.setPen(QPen(QColor(0, 0, 0), 1))
            
            # 绘制文字（居中对齐）
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
                hit_rect = rect.adjusted(-5, -5, 5, 5)
                
                if hit_rect.contains(event.pos()):
                    clicked_index = i
                    break
            
            if clicked_index >= 0:
                self.selected_index = clicked_index
                for i, item in enumerate(self.text_items):
                    item.selected = (i == clicked_index)
                
                # 开始拖动
                self.drag_start_pos = event.pos()
                item = self.text_items[clicked_index]
                self.drag_original_pos = (item.x, item.y)
                self.is_dragging_move = False
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
                
                # 计算鼠标移动总偏移
                dx_screen = event.x() - self.drag_start_pos.x()
                dy_screen = event.y() - self.drag_start_pos.y()
                
                # 只有当移动距离超过阈值才视为拖动
                if (dx_screen**2 + dy_screen**2) > 9:  # 3 pixels
                    self.is_dragging_move = True
                
                # 转换到逻辑距离
                dx_logical = dx_screen / scale
                dy_logical = -dy_screen / scale  # Y轴反转
                
                # 基于原始位置计算新位置
                orig_x, orig_y = self.drag_original_pos
                new_x = orig_x + dx_logical
                new_y = orig_y + dy_logical
                
                # 更新文字位置
                item = self.text_items[self.selected_index]
                item.x = new_x
                item.y = new_y
                
                # 更新配置中的offset
                if self.config:
                    pos_idx = item.pos_idx
                    base_x, base_y = _calculate_base_position(
                        pos_idx, 
                        u_to_mm(self.key_type.width), 
                        u_to_mm(self.key_type.height)
                    )
                    # 计算新的offset
                    new_offset_x = new_x - base_x
                    new_offset_y = new_y - base_y
                    
                    # 更新样式
                    if pos_idx in self.config.text_styles:
                        self.config.text_styles[pos_idx].offset_x = new_offset_x
                        self.config.text_styles[pos_idx].offset_y = new_offset_y
                    else:
                        from core.legend_mapping import LegendStyle
                        self.config.text_styles[pos_idx] = LegendStyle(
                            offset_x=new_offset_x,
                            offset_y=new_offset_y
                        )
                    
                    # 发出位置改变信号
                    self.position_changed.emit(pos_idx, new_offset_x, new_offset_y)
                
                self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.is_dragging_move:
            self.is_dragging_move = False
            self.drag_start_pos = None
            self.drag_original_pos = None
