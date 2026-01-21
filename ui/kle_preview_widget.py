"""
KLE 布局 2D 预览控件
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QPalette
from typing import List, Optional
from core.kle_parser import KLEKey

class KLEPreviewWidget(QWidget):
    """KLE 布局 2D 预览控件"""
    
    # 信号：选中按键索引（单击）
    key_selected = pyqtSignal(int)
    # 信号：双击按键索引（打开编辑对话框）
    key_double_clicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.keys: List[KLEKey] = []
        self.selected_index: int = -1
        self.scale_factor: float = 40.0 # 1u = 40px
        self.margin: float = 20.0
        # 初始间距设为0（u单位），等待set_spacing设置正确的值
        # 默认2.0 u单位相当于38.1mm，太大了
        self.row_spacing: float = 0.0  # 行间距 (u单位，与KLE坐标系统一致)
        self.col_spacing: float = 0.0  # 列间距 (u单位)
        self.key_display_positions: dict = {}  # {key_index: (display_x, display_y)} 存储应用间距后的显示位置
        self.setMouseTracking(True)
        self.setBackgroundRole(QPalette.NoRole)
    
    def set_spacing(self, row_spacing: float, col_spacing: float):
        """设置间距（mm单位，内部转换为u单位）"""
        from core.keycap_presets import mm_to_u
        self.row_spacing = mm_to_u(row_spacing)
        self.col_spacing = mm_to_u(col_spacing)
        self.update()

    def set_data(self, keys: List[KLEKey]):
        """设置数据"""
        self.keys = keys
        self.selected_index = -1
        # 如果间距还没有被设置（仍然是初始值0.0），使用默认值
        # 默认2.0mm转换为u单位（约0.105u）
        if self.row_spacing == 0.0 and self.col_spacing == 0.0:
            from core.keycap_presets import mm_to_u
            self.row_spacing = mm_to_u(2.0)  # 默认2.0mm
            self.col_spacing = mm_to_u(2.0)  # 默认2.0mm
        # 强制重新计算缩放和显示位置
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

        # 计算自动缩放
        self._calculate_scale()
        
        # 移动坐标系到中心或边距
        painter.translate(self.margin, self.margin)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # 按行分组按键（应用间距）
        rows = {}
        for key in self.keys:
            row_y = key.y
            if row_y not in rows:
                rows[row_y] = []
            rows[row_y].append(key)
        
        sorted_rows = sorted(rows.keys())
        
        # Y轴向下（Qt屏幕坐标系），从顶部开始
        current_y = 0.0  # 第一行从Y=0开始（顶部）
        max_row_height = 0.0
        
        # 存储按键的显示位置映射（用于鼠标点击检测）
        self.key_display_positions = {}  # {key_index: (display_x, display_y)}
        
        for row_idx, row_y in enumerate(sorted_rows):
            row_keys = sorted(rows[row_y], key=lambda k: k.x)
            current_x = 0.0  # 每行从x=0开始
            
            for key in row_keys:
                # 计算按键显示位置（应用间距）
                # current_y是当前行的顶部Y位置，按键的y位置就是current_y（按键顶部）
                key_x = current_x
                key_y = current_y  # 按键顶部位置
                
                # 绘制按键（使用计算后的位置）
                key_index = self.keys.index(key) if key in self.keys else -1
                if key_index >= 0:
                    # 保存显示位置（保存按键左上角位置）
                    self.key_display_positions[key_index] = (key_x, key_y)
                    
                    # 创建临时按键对象用于绘制（避免修改原始数据）
                    temp_key = KLEKey(
                        x=key_x, y=key_y,
                        width=key.width, height=key.height,
                        rotation_angle=key.rotation_angle,
                        rotation_x=key.rotation_x, rotation_y=key.rotation_y,
                        labels=key.labels.copy(),
                        text_color=key.text_color,
                        key_color=key.key_color,
                        font_sizes=key.font_sizes.copy() if key.font_sizes else [],
                        alignment=key.alignment,
                        profile=key.profile,
                        row=key.row
                    )
                    self._draw_key(painter, key_index, temp_key)
                
                # 更新下一个按键的x位置
                current_x += key.width + self.col_spacing
                max_row_height = max(max_row_height, key.height)
            
            # 换行：更新y位置（Y轴向下，所以加上）
            current_y += max_row_height + self.row_spacing
            max_row_height = 0.0
            
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
        
        # 颜色
        if index == self.selected_index:
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
            
            # 计算合适的字体大小（按键宽度的 25%，最小 6px，最大 20px）
            font_size_px = max(6, min(20, int(key_w_px * 0.25)))
            
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
        """计算适应窗口的缩放比例（考虑间距）"""
        if not self.keys:
            return
        
        # 按行分组按键并计算应用间距后的边界框
        rows = {}
        for key in self.keys:
            row_y = key.y
            if row_y not in rows:
                rows[row_y] = []
            rows[row_y].append(key)
        
        sorted_rows = sorted(rows.keys())
        
        # Y轴向下（Qt屏幕坐标系），从顶部开始（与绘制逻辑一致）
        current_y = 0.0  # 第一行从Y=0开始
        max_row_height = 0.0
        min_x = 0.0
        max_x = 0.0
        min_y = 0.0
        max_y = 0.0
        
        for row_idx, row_y in enumerate(sorted_rows):
            row_keys = sorted(rows[row_y], key=lambda k: k.x)
            current_x = 0.0
            
            for key in row_keys:
                # 计算按键显示位置
                key_x = current_x
                key_y = current_y  # 按键顶部位置
                
                # 更新边界框
                min_x = min(min_x, key_x)
                max_x = max(max_x, key_x + key.width)
                min_y = min(min_y, key_y)
                max_y = max(max_y, key_y + key.height)
                
                # 更新下一个按键的x位置
                current_x += key.width + self.col_spacing
                max_row_height = max(max_row_height, key.height)
            
            # 换行（Y轴向下，所以加上）
            current_y += max_row_height + self.row_spacing
            max_row_height = 0.0
        
        content_w = max_x - min_x
        content_h = max_y - min_y
        
        if content_w <= 0 or content_h <= 0:
            return
            
        # 窗口尺寸
        view_w = self.width() - 2 * self.margin
        view_h = self.height() - 2 * self.margin
        
        # 计算比例
        scale_x = view_w / content_w
        scale_y = view_h / content_h
        
        self.scale_factor = min(scale_x, scale_y)
    
    def mousePressEvent(self, event):
        """处理点击选中（考虑间距）"""
        # 将鼠标坐标转换为逻辑坐标并查找按键
        click_pos = event.pos()
        # 转换为相对 margin 的坐标
        mx = click_pos.x() - self.margin
        my = click_pos.y() - self.margin
        # 转换为 u 单位
        u_x = mx / self.scale_factor
        u_y = my / self.scale_factor
        
        # 查找匹配的按键（使用应用间距后的显示位置）
        found = -1
        if hasattr(self, 'key_display_positions'):
            for i, key in enumerate(self.keys):
                if i in self.key_display_positions:
                    display_x, display_y = self.key_display_positions[i]
                    # 使用显示位置进行点击检测
                    if (display_x <= u_x <= display_x + key.width and
                        display_y <= u_y <= display_y + key.height):
                        found = i
                        break
        else:
            # 如果没有显示位置映射，使用原始位置（向后兼容）
            for i, key in enumerate(self.keys):
                if (key.x <= u_x <= key.x + key.width and
                    key.y <= u_y <= key.y + key.height):
                    found = i
                    break # 找到顶层的一个（KLE 也是后绘制的在上面）
        
        if found != -1:
            self.selected_index = found
            self.key_selected.emit(found)
            self.update()
        else:
            self.selected_index = -1
            self.update()
    
    def mouseDoubleClickEvent(self, event):
        """处理双击事件 - 打开编辑对话框"""
        # 复用点击检测逻辑
        click_pos = event.pos()
        mx = click_pos.x() - self.margin
        my = click_pos.y() - self.margin
        u_x = mx / self.scale_factor
        u_y = my / self.scale_factor
        
        # 查找匹配的按键
        found = -1
        for i, key in enumerate(self.keys):
            if (key.x <= u_x <= key.x + key.width and
                key.y <= u_y <= key.y + key.height):
                found = i
                break
        
        if found != -1:
            # 发出双击信号
            self.key_double_clicked.emit(found)
