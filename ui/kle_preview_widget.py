"""
KLE 布局 2D 预览控件
"""
from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QPalette
from typing import List, Optional
from core.kle_parser import KLEKey
from core.legend_mapping import KLE_POSITION_NAMES

class KLEPreviewWidget(QWidget):
    """KLE 布局 2D 预览控件"""
    
    # 信号：选中按键索引（单击，兼容旧逻辑）
    key_selected = pyqtSignal(int)
    # 信号：选中变化（支持多选，list 为当前选中的索引）
    key_selection_changed = pyqtSignal(list)
    # 信号：双击按键索引（打开编辑对话框）
    key_double_clicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.keys: List[KLEKey] = []
        self.selected_index: int = -1  # 主选中（多选时取第一个）
        self.selected_indices: List[int] = []  # 多选列表，支持框选、Ctrl+点击
        self._drag_start: Optional[QPointF] = None  # 框选起点（像素）
        self._drag_current: Optional[QPointF] = None  # 框选当前点（用于绘制橡皮筋）
        self.scale_factor: float = 40.0 # 1u = 40px
        self.margin: float = 20.0
        # 初始间距设为0（u单位），等待set_spacing设置正确的值
        # 默认2.0 u单位相当于38.1mm，太大了
        # 2D 预览固定使用 0 间距，仅反映键盘形状；模型间距只影响 3D 生成
        self._preview_row_spacing: float = 0.0
        self._preview_col_spacing: float = 0.0
        self.key_display_positions: dict = {}  # {key_index: (display_x, display_y)}
        self.setMouseTracking(True)
        self.setBackgroundRole(QPalette.NoRole)
    
    def set_spacing(self, row_spacing: float, col_spacing: float):
        """设置间距（mm 单位）。仅保留接口兼容，2D 预览始终使用 0 间距，不影响布局。"""
        pass

    def set_data(self, keys: List[KLEKey]):
        """设置数据"""
        self.keys = keys
        self.selected_index = -1
        self.selected_indices = []
        self._drag_start = None
        self._drag_current = None
        self._calculate_scale()
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor("#f0f0f0"))
        
        if not self.keys:
            painter.drawText(self.rect(), Qt.AlignCenter, "请在左侧导入 KLE 数据")
            return

        # 计算自动缩放（使用 KLE 解析出的 key.x/key.y，保留布局中的间隔）
        self._calculate_scale()
        
        # 移动坐标系到中心或边距
        painter.translate(self.margin, self.margin)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # 按 key.x, key.y 直接绘制（保留数字区与字母区等布局间隔）
        for key_index, key in enumerate(self.keys):
            self._draw_key(painter, key_index, key)
        
        # 框选橡皮筋：在窗口坐标系下绘制选择矩形
        if self._drag_start is not None and self._drag_current is not None:
            painter.save()
            painter.resetTransform()
            x1, x2 = self._drag_start.x(), self._drag_current.x()
            y1, y2 = self._drag_start.y(), self._drag_current.y()
            r = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            painter.setPen(QPen(QColor("#0066cc"), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(0, 102, 204, 40)))
            painter.drawRect(r)
            painter.restore()
            
    def _draw_key(self, painter: QPainter, index: int, key: KLEKey):
        """绘制单个按键"""
        # 保存状态
        painter.save()
        
        # 应用位置和旋转
        # KLE 旋转逻辑：围绕 (rotation_x, rotation_y) 旋转 rotation_angle
        if key.rotation_angle != 0:
            painter.translate(key.rotation_x, key.rotation_y)
            painter.rotate(key.rotation_angle)
            painter.translate(-key.rotation_x, -key.rotation_y)
            
        painter.translate(key.x, key.y)
        
        # 绘制矩形
        rect = QRectF(0, 0, key.width, key.height)
        
        # 颜色（多选时任意选中即高亮）
        if index in self.selected_indices:
            fill_color = QColor("#aaddff")
            border_color = QColor("#0066cc")
            border_width = 0.1
        else:
            fill_color = QColor(key.key_color)
            border_color = QColor("#666666")
            border_width = 0.05
            
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(fill_color))
        
        # 简单的圆角矩形 (约 2px 在 40px 比例下是 0.05u)
        radius = 0.1
        painter.drawRoundedRect(rect, radius, radius)
        
        painter.restore()
        
        # 绘制文字（在按键矩形之外，使用像素坐标）
        # KLE 的12个位置映射：
        # 顶面：左上0, 中上8, 右上2, 左中6, 正中9, 右中7, 左下1, 中下10, 右下3
        # 侧刻：左侧4, 中间11, 右侧5
        if key.labels:
            # 计算按键在屏幕上的实际像素位置和大小
            key_x_px = (key.x * self.scale_factor) + self.margin
            key_y_px = (key.y * self.scale_factor) + self.margin
            key_w_px = key.width * self.scale_factor
            key_h_px = key.height * self.scale_factor
            
            # 计算合适的字体大小（按键宽度的 38%，最小 9px，最大 32px，便于在 2D 预览中看清）
            font_size_px = max(9, min(32, int(key_w_px * 0.38)))
            
            # 保存当前变换状态
            painter.save()
            
            # 重置变换，使用像素坐标
            painter.resetTransform()
            
            # 设置字体和颜色
            font = painter.font()
            font.setPixelSize(font_size_px)
            painter.setFont(font)
            painter.setPen(QColor(key.text_color))
            
            # 位置对齐映射 (KLE 索引 -> Qt 对齐标志)
            # 顶面位置
            position_map = {
                0: (Qt.AlignLeft | Qt.AlignTop),      # 左上
                8: (Qt.AlignHCenter | Qt.AlignTop),   # 中上
                2: (Qt.AlignRight | Qt.AlignTop),     # 右上
                6: (Qt.AlignLeft | Qt.AlignVCenter),  # 左中
                9: (Qt.AlignCenter),                  # 正中
                7: (Qt.AlignRight | Qt.AlignVCenter), # 右中
                1: (Qt.AlignLeft | Qt.AlignBottom),   # 左下
                10: (Qt.AlignHCenter | Qt.AlignBottom), # 中下
                3: (Qt.AlignRight | Qt.AlignBottom),  # 右下
                # 侧刻位置（在预览中暂时不显示，或显示在侧面）
                4: (Qt.AlignLeft | Qt.AlignVCenter),  # 左侧（侧刻）
                11: (Qt.AlignHCenter | Qt.AlignVCenter), # 中间（侧刻）
                5: (Qt.AlignRight | Qt.AlignVCenter), # 右侧（侧刻）
            }
            
            # 绘制所有非空字符
            for pos_idx, label_text in enumerate(key.labels):
                if label_text and label_text.strip():  # 非空字符
                    align = position_map.get(pos_idx, Qt.AlignCenter)
                    text_rect = QRectF(key_x_px, key_y_px, key_w_px, key_h_px)
                    
                    # 处理换行符：如果文本包含换行符，需要多行绘制
                    if '\n' in label_text:
                        # 分割为多行
                        lines = label_text.split('\n')
                        # 计算每行的高度
                        line_height = font_size_px + 2
                        total_height = len(lines) * line_height
                        
                        # 根据对齐方式计算起始y位置
                        if align & Qt.AlignTop:
                            start_y = text_rect.y()
                        elif align & Qt.AlignBottom:
                            start_y = text_rect.y() + text_rect.height() - total_height
                        else:  # 垂直居中
                            start_y = text_rect.y() + (text_rect.height() - total_height) / 2
                        
                        # 绘制每一行
                        for line_idx, line in enumerate(lines):
                            if line.strip():  # 只绘制非空行
                                line_rect = QRectF(
                                    text_rect.x(),
                                    start_y + line_idx * line_height,
                                    text_rect.width(),
                                    line_height
                                )
                                # 水平对齐
                                if align & Qt.AlignLeft:
                                    line_align = Qt.AlignLeft | Qt.AlignVCenter
                                elif align & Qt.AlignRight:
                                    line_align = Qt.AlignRight | Qt.AlignVCenter
                                else:  # 水平居中
                                    line_align = Qt.AlignHCenter | Qt.AlignVCenter
                                
                                # 对于侧刻位置（4, 11, 5），可以稍微偏移或使用不同颜色
                                if pos_idx in [4, 11, 5]:
                                    painter.setPen(QColor("#888888"))
                                    line_rect = QRectF(key_x_px, key_y_px + key_h_px + 2 + line_idx * line_height, key_w_px, line_height)
                                    painter.drawText(line_rect, Qt.AlignHCenter | Qt.AlignVCenter, line.strip())
                                    painter.setPen(QColor(key.text_color))  # 恢复颜色
                                else:
                                    painter.drawText(line_rect, line_align, line.strip())
                    else:
                        # 单行文本（原有逻辑）
                        # 对于侧刻位置（4, 11, 5），可以稍微偏移或使用不同颜色
                        if pos_idx in [4, 11, 5]:
                            # 侧刻字符可以显示在按键下方或使用灰色
                            painter.setPen(QColor("#888888"))
                            # 稍微向下偏移
                            text_rect = QRectF(key_x_px, key_y_px + key_h_px + 2, key_w_px, font_size_px + 4)
                            painter.drawText(text_rect, Qt.AlignHCenter, label_text)
                            painter.setPen(QColor(key.text_color))  # 恢复颜色
                        else:
                            # 顶面字符
                            painter.drawText(text_rect, align, label_text)
            
            # 恢复变换状态
            painter.restore()

    def _calculate_scale(self):
        """计算适应窗口的缩放比例；使用 KLE 的 key.x/key.y 作为显示位置，保留布局间隔"""
        if not self.keys:
            return
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        self.key_display_positions = {}
        
        for i, key in enumerate(self.keys):
            self.key_display_positions[i] = (key.x, key.y)
            min_x = min(min_x, key.x)
            max_x = max(max_x, key.x + key.width)
            min_y = min(min_y, key.y)
            max_y = max(max_y, key.y + key.height)
        
        content_w = max_x - min_x
        content_h = max_y - min_y
        
        if content_w <= 0 or content_h <= 0:
            return
            
        view_w = self.width() - 2 * self.margin
        view_h = self.height() - 2 * self.margin
        
        scale_x = view_w / content_w
        scale_y = view_h / content_h
        self.scale_factor = min(scale_x, scale_y)
    
    def _key_index_at(self, u_x: float, u_y: float) -> int:
        """根据逻辑坐标 (u 单位) 返回光标下的按键索引，若无则返回 -1。"""
        self._calculate_scale()
        for i, key in enumerate(self.keys):
            if i in self.key_display_positions:
                dx, dy = self.key_display_positions[i]
                if dx <= u_x <= dx + key.width and dy <= u_y <= dy + key.height:
                    return i
        return -1
    
    def _key_indices_in_rect(self, top_left: QPointF, bottom_right: QPointF) -> List[int]:
        """屏幕坐标系下矩形范围内的按键索引列表（用于框选）。"""
        self._calculate_scale()
        mx, my = self.margin, self.margin
        u_x1 = (min(top_left.x(), bottom_right.x()) - mx) / self.scale_factor
        u_y1 = (min(top_left.y(), bottom_right.y()) - my) / self.scale_factor
        u_x2 = (max(top_left.x(), bottom_right.x()) - mx) / self.scale_factor
        u_y2 = (max(top_left.y(), bottom_right.y()) - my) / self.scale_factor
        out = []
        for i, key in enumerate(self.keys):
            if i not in self.key_display_positions:
                continue
            dx, dy = self.key_display_positions[i]
            # 按键矩形与选择矩形有交即选中
            if u_x2 >= dx and u_x1 <= dx + key.width and u_y2 >= dy and u_y1 <= dy + key.height:
                out.append(i)
        return out
    
    def _emit_selection(self):
        """同步 selected_index 并发出选中变化信号。"""
        self.selected_index = self.selected_indices[0] if self.selected_indices else -1
        self.key_selection_changed.emit(list(self.selected_indices))
        self.key_selected.emit(self.selected_index)
    
    def mouseMoveEvent(self, event):
        """悬停时显示气泡；拖动时更新橡皮筋"""
        if self._drag_start is not None:
            self._drag_current = QPointF(event.pos())
            self.update()
        else:
            mx = event.pos().x() - self.margin
            my = event.pos().y() - self.margin
            u_x = mx / self.scale_factor
            u_y = my / self.scale_factor
            idx = self._key_index_at(u_x, u_y)
            if idx >= 0 and idx < len(self.keys):
                key = self.keys[idx]
                parts = []
                for pos_idx, label in enumerate(key.labels or []):
                    if label and str(label).strip():
                        pos_name = KLE_POSITION_NAMES.get(pos_idx, f"位置{pos_idx}")
                        parts.append(f"{pos_name}: {label.strip()}")
                if parts:
                    tip = "\n".join(parts)
                    g = self.mapToGlobal(event.pos())
                    QToolTip.showText(g, tip, self, self.rect(), 2000)
                else:
                    QToolTip.hideText()
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """处理点击选中、Ctrl+多选、框选起点"""
        if event.button() != Qt.LeftButton:
            return
        self._drag_start = QPointF(event.pos())
        mx = event.pos().x() - self.margin
        my = event.pos().y() - self.margin
        u_x = mx / self.scale_factor
        u_y = my / self.scale_factor
        found = self._key_index_at(u_x, u_y)
        if found != -1:
            if event.modifiers() & Qt.ControlModifier:
                if found in self.selected_indices:
                    self.selected_indices = [i for i in self.selected_indices if i != found]
                else:
                    self.selected_indices = list(self.selected_indices) + [found]
            else:
                self.selected_indices = [found]
        else:
            if not (event.modifiers() & Qt.ControlModifier):
                self.selected_indices = []
        self._emit_selection()
        self.update()
    
    def mouseReleaseEvent(self, event):
        """框选结束：若拖动距离足够则按矩形范围更新多选，并清除橡皮筋"""
        if event.button() == Qt.LeftButton and self._drag_start is not None:
            p1, p2 = self._drag_start, QPointF(event.pos())
            if abs(p2.x() - p1.x()) > 6 or abs(p2.y() - p1.y()) > 6:
                indices = self._key_indices_in_rect(p1, p2)
                if indices:
                    self.selected_indices = indices
                    self._emit_selection()
            self._drag_start = None
            self._drag_current = None
            self.update()
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """处理双击事件 - 打开编辑对话框"""
        mx = event.pos().x() - self.margin
        my = event.pos().y() - self.margin
        u_x = mx / self.scale_factor
        u_y = my / self.scale_factor
        found = self._key_index_at(u_x, u_y)
        if found != -1:
            self.key_double_clicked.emit(found)
