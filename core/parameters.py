"""
参数管理类
定义和管理按键模型的所有参数
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class KeycapGeometry:
    """按键几何参数类 (不包含字符)"""
    # 按键尺寸 (mm)
    key_width: float = 18.0      # 按键宽度
    key_height: float = 18.0     # 按键高度
    key_depth: float = 8.0       # 按键深度（从顶部到底部）
    
    # 按键尺寸单位（u单位）
    key_width_u: float = 1.0     # 按键宽度（u单位）
    key_height_u: float = 1.0    # 按键高度（u单位）
    use_u_units: bool = False    # 是否使用u单位
    
    # 键帽高度预设
    height_profile: str = "Cherry高度"  # 高度预设名称
    keycap_row: str = "R3"      # 键帽行号 (R1, R2, R3, R4)
    
    # 斜角参数 (度)
    side_angle: float = 0.0      # 侧面斜角
    
    # 边缘形状参数 (mm)
    edge_profile_mode: str = "fillet"  # "fillet"(圆角) 或 "chamfer"(45度斜角)
    edge_profile_radius: float = 0.0  # 边缘圆角/倒角半径 (mm)
    edge_profile_outer: bool = True  # 外侧边缘生效
    edge_profile_inner: bool = False  # 内侧边缘生效（与外侧形成拱形）
    edge_profile_left: bool = True   # 左侧边
    edge_profile_right: bool = True  # 右侧边
    edge_profile_top: bool = True    # 上侧边
    edge_profile_bottom: bool = True # 下侧边
    
    # 结构参数 (mm)
    wall_thickness: float = 1.0   # 壁厚（侧面厚度）
    top_thickness: float = 1.0    # 顶面厚度
    corner_radius: float = 0.5    # 圆角半径
    
    # 轴体类型
    stem_type: str = "MX"        # 轴体类型: MX, Alps等
    
    # 连接器参数
    stem_enabled: bool = True    # 是否生成连接器
    stem_height: float = 4.0     # 连接器深度 (mm)
    stem_cylinder_diameter: float = 5.4  # 圆柱直径 (mm)
    stem_cross_width: float = 1.0  # 十字宽度 (mm)
    stem_cross_length: float = 4.0  # 十字长度 (mm)
    
    # 卫星轴参数（用于长按键，如空格键、Shift等）
    stabilizer_enabled: bool = False  # 是否添加卫星轴连接器
    stabilizer_length: float = 50.0   # 卫星轴长度 (mm)，通常为按键宽度的2-3倍
    
    # 弧面参数
    curved_top_enabled: bool = False  # 是否启用弧面
    curved_top_x_enabled: bool = False  # X方向弧面
    curved_top_y_enabled: bool = False  # Y方向弧面
    curved_top_x_radius: float = 90.0  # X方向圆弧半径 (mm)，默认5倍按键宽度
    curved_top_y_radius: float = 90.0  # Y方向圆弧半径 (mm)，默认5倍按键高度
    curved_top_direction: str = "convex"  # 弧面方向: "convex"(向上凸起) 或 "concave"(向下凹陷)

    def validate(self) -> tuple[bool, str]:
        if self.key_width <= 0 or self.key_height <= 0 or self.key_depth <= 0:
            return False, "按键尺寸必须大于0"
        if self.wall_thickness <= 0:
            return False, "壁厚必须大于0"
        if self.side_angle < 0 or self.side_angle > 30:
            return False, "侧面斜角必须在0-30度之间"
        if self.edge_profile_radius < 0:
            return False, "边缘半径必须大于等于0"
        # 验证弧面参数
        if self.curved_top_enabled:
            # 计算实际的顶面尺寸（考虑侧面斜角）
            from math import tan, radians
            side_angle_rad = radians(self.side_angle)
            top_w = self.key_width - 2 * self.key_depth * tan(side_angle_rad) if side_angle_rad > 0 else self.key_width
            top_h = self.key_height - 2 * self.key_depth * tan(side_angle_rad) if side_angle_rad > 0 else self.key_height
            
            if self.curved_top_x_enabled:
                if 2 * self.curved_top_x_radius < top_w:
                    return False, f"X方向圆弧直径({2*self.curved_top_x_radius:.2f}mm)必须 >= 顶面宽度({top_w:.2f}mm，已考虑侧面斜角)"
            if self.curved_top_y_enabled:
                if 2 * self.curved_top_y_radius < top_h:
                    return False, f"Y方向圆弧直径({2*self.curved_top_y_radius:.2f}mm)必须 >= 顶面高度({top_h:.2f}mm，已考虑侧面斜角)"
            if self.curved_top_direction not in ["convex", "concave"]:
                return False, "弧面方向必须是 'convex'(凸起) 或 'concave'(凹陷)"
        return True, ""


@dataclass
class TextParameters:
    """单个文字/字符的参数"""
    text: str = "A"              # 文字内容（支持长文本、中文、多字符）
    font_path: Optional[str] = None  # 字体文件路径
    size: float = 3.0            # 文字高度 (mm)
    depth: float = 0.5           # 文字深度 (mm)，正值凹陷、负值凸起
    offset_x: float = 0.0        # 文字X偏移 (mm)
    offset_y: float = 0.0        # 文字Y偏移 (mm)
    stroke_width: float = 0.0    # 线宽/描边加粗 (mm)，>0 时向外扩展轮廓，避免细线打印被跳过
    bold: bool = False           # 加粗（额外描边）
    italic: bool = False        # 斜体（几何剪切）
    underline: bool = False     # 下划线
    
    def validate(self) -> tuple[bool, str]:
        if not self.text:
            return False, "字符内容不能为空"
        if self.size <= 0:
            return False, "文字大小必须大于0"
        return True, ""


@dataclass
class ImageParameters:
    """单张图片的参数"""
    path: str = ""               # 图片文件路径
    depth: float = 0.5           # 挤出深度 (mm)，正值凹陷、负值凸起
    offset_x: float = 0.0        # X 偏移 (mm)
    offset_y: float = 0.0        # Y 偏移 (mm)
    size: float = 6.0            # 在键帽上的最大尺寸 (mm)，保持比例
    scale: float = 1.0           # 缩放比例，1.0=100%，最终尺寸= size*scale
    threshold: int = 128         # 二值化阈值 0–255，决定明暗分界
    invert: bool = False         # 是否反转：False=深色区域凸起/凹陷，True=浅色区域
    
    def validate(self) -> tuple[bool, str]:
        if not self.path or not self.path.strip():
            return False, "图片路径不能为空"
        if self.size <= 0:
            return False, "图片尺寸必须大于0"
        if self.scale <= 0:
            return False, "图片缩放必须大于0"
        if not (0 <= self.threshold <= 255):
            return False, "阈值必须在 0–255 之间"
        return True, ""


@dataclass
class KeycapDesign:
    """完整按键设计 (几何 + 文字 + 图片)"""
    # 核心几何参数
    geometry: KeycapGeometry = field(default_factory=KeycapGeometry)
    
    # 文字列表 (主要数据源)
    text_items: List[TextParameters] = field(default_factory=list)
    
    # 图片列表
    image_items: List[ImageParameters] = field(default_factory=list)
    
    # --- 兼容旧版属性 (通过 property 代理访问) ---
    
    @property
    def key_width(self): return self.geometry.key_width
    @key_width.setter
    def key_width(self, v): self.geometry.key_width = v
    
    @property
    def key_height(self): return self.geometry.key_height
    @key_height.setter
    def key_height(self, v): self.geometry.key_height = v
    
    @property
    def key_depth(self): return self.geometry.key_depth
    @key_depth.setter
    def key_depth(self, v): self.geometry.key_depth = v

    @property
    def key_width_u(self): return self.geometry.key_width_u
    @key_width_u.setter
    def key_width_u(self, v): self.geometry.key_width_u = v

    @property
    def key_height_u(self): return self.geometry.key_height_u
    @key_height_u.setter
    def key_height_u(self, v): self.geometry.key_height_u = v

    @property
    def use_u_units(self): return self.geometry.use_u_units
    @use_u_units.setter
    def use_u_units(self, v): self.geometry.use_u_units = v
    
    @property
    def height_profile(self): return self.geometry.height_profile
    @height_profile.setter
    def height_profile(self, v): self.geometry.height_profile = v

    @property
    def keycap_row(self): return self.geometry.keycap_row
    @keycap_row.setter
    def keycap_row(self, v): self.geometry.keycap_row = v

    @property
    def side_angle(self): return self.geometry.side_angle
    @side_angle.setter
    def side_angle(self, v): self.geometry.side_angle = v
    
    @property
    def wall_thickness(self): return self.geometry.wall_thickness
    @wall_thickness.setter
    def wall_thickness(self, v): self.geometry.wall_thickness = v

    @property
    def top_thickness(self): return self.geometry.top_thickness
    @top_thickness.setter
    def top_thickness(self, v): self.geometry.top_thickness = v

    @property
    def corner_radius(self): return self.geometry.corner_radius
    @corner_radius.setter
    def corner_radius(self, v): self.geometry.corner_radius = v
    
    @property
    def edge_profile_mode(self): return self.geometry.edge_profile_mode
    @edge_profile_mode.setter
    def edge_profile_mode(self, v): self.geometry.edge_profile_mode = v

    @property
    def edge_profile_radius(self): return self.geometry.edge_profile_radius
    @edge_profile_radius.setter
    def edge_profile_radius(self, v): self.geometry.edge_profile_radius = v

    @property
    def edge_profile_outer(self): return self.geometry.edge_profile_outer
    @edge_profile_outer.setter
    def edge_profile_outer(self, v): self.geometry.edge_profile_outer = v

    @property
    def edge_profile_inner(self): return self.geometry.edge_profile_inner
    @edge_profile_inner.setter
    def edge_profile_inner(self, v): self.geometry.edge_profile_inner = v

    @property
    def edge_profile_left(self): return self.geometry.edge_profile_left
    @edge_profile_left.setter
    def edge_profile_left(self, v): self.geometry.edge_profile_left = v

    @property
    def edge_profile_right(self): return self.geometry.edge_profile_right
    @edge_profile_right.setter
    def edge_profile_right(self, v): self.geometry.edge_profile_right = v

    @property
    def edge_profile_top(self): return self.geometry.edge_profile_top
    @edge_profile_top.setter
    def edge_profile_top(self, v): self.geometry.edge_profile_top = v

    @property
    def edge_profile_bottom(self): return self.geometry.edge_profile_bottom
    @edge_profile_bottom.setter
    def edge_profile_bottom(self, v): self.geometry.edge_profile_bottom = v

    @property
    def stem_type(self): return self.geometry.stem_type
    @stem_type.setter
    def stem_type(self, v): self.geometry.stem_type = v

    @property
    def stem_enabled(self): return self.geometry.stem_enabled
    @stem_enabled.setter
    def stem_enabled(self, v): self.geometry.stem_enabled = v

    @property
    def stem_height(self): return self.geometry.stem_height
    @stem_height.setter
    def stem_height(self, v): self.geometry.stem_height = v

    @property
    def stem_cylinder_diameter(self): return self.geometry.stem_cylinder_diameter
    @stem_cylinder_diameter.setter
    def stem_cylinder_diameter(self, v): self.geometry.stem_cylinder_diameter = v

    @property
    def stem_cross_width(self): return self.geometry.stem_cross_width
    @stem_cross_width.setter
    def stem_cross_width(self, v): self.geometry.stem_cross_width = v

    @property
    def stem_cross_length(self): return self.geometry.stem_cross_length
    @stem_cross_length.setter
    def stem_cross_length(self, v): self.geometry.stem_cross_length = v
    
    @property
    def stabilizer_enabled(self): return getattr(self.geometry, 'stabilizer_enabled', False)
    @stabilizer_enabled.setter
    def stabilizer_enabled(self, v): 
        if not hasattr(self.geometry, 'stabilizer_enabled'):
            setattr(self.geometry, 'stabilizer_enabled', v)
        else:
            self.geometry.stabilizer_enabled = v
    
    @property
    def stabilizer_length(self): return getattr(self.geometry, 'stabilizer_length', 50.0)
    @stabilizer_length.setter
    def stabilizer_length(self, v): 
        if not hasattr(self.geometry, 'stabilizer_length'):
            setattr(self.geometry, 'stabilizer_length', v)
        else:
            self.geometry.stabilizer_length = v
    
    # 弧面参数兼容
    @property
    def curved_top_enabled(self): return getattr(self.geometry, 'curved_top_enabled', False)
    @curved_top_enabled.setter
    def curved_top_enabled(self, v): 
        if not hasattr(self.geometry, 'curved_top_enabled'):
            setattr(self.geometry, 'curved_top_enabled', v)
        else:
            self.geometry.curved_top_enabled = v
    
    @property
    def curved_top_x_enabled(self): return getattr(self.geometry, 'curved_top_x_enabled', False)
    @curved_top_x_enabled.setter
    def curved_top_x_enabled(self, v): 
        if not hasattr(self.geometry, 'curved_top_x_enabled'):
            setattr(self.geometry, 'curved_top_x_enabled', v)
        else:
            self.geometry.curved_top_x_enabled = v
    
    @property
    def curved_top_y_enabled(self): return getattr(self.geometry, 'curved_top_y_enabled', False)
    @curved_top_y_enabled.setter
    def curved_top_y_enabled(self, v): 
        if not hasattr(self.geometry, 'curved_top_y_enabled'):
            setattr(self.geometry, 'curved_top_y_enabled', v)
        else:
            self.geometry.curved_top_y_enabled = v
    
    @property
    def curved_top_x_radius(self): return getattr(self.geometry, 'curved_top_x_radius', 90.0)
    @curved_top_x_radius.setter
    def curved_top_x_radius(self, v): 
        if not hasattr(self.geometry, 'curved_top_x_radius'):
            setattr(self.geometry, 'curved_top_x_radius', v)
        else:
            self.geometry.curved_top_x_radius = v
    
    @property
    def curved_top_y_radius(self): return getattr(self.geometry, 'curved_top_y_radius', 90.0)
    @curved_top_y_radius.setter
    def curved_top_y_radius(self, v): 
        if not hasattr(self.geometry, 'curved_top_y_radius'):
            setattr(self.geometry, 'curved_top_y_radius', v)
        else:
            self.geometry.curved_top_y_radius = v
    
    @property
    def curved_top_direction(self): return getattr(self.geometry, 'curved_top_direction', 'convex')
    @curved_top_direction.setter
    def curved_top_direction(self, v): 
        if not hasattr(self.geometry, 'curved_top_direction'):
            setattr(self.geometry, 'curved_top_direction', v)
        else:
            self.geometry.curved_top_direction = v
    
    # 字符参数兼容 (默认操作第一个字符，如果没有则创建一个默认的)
    def _ensure_primary_text(self):
        if not self.text_items:
            self.text_items.append(TextParameters())
        return self.text_items[0]

    @property
    def letter(self): return self._ensure_primary_text().text
    @letter.setter
    def letter(self, v): self._ensure_primary_text().text = v
    
    @property
    def font_path(self): return self._ensure_primary_text().font_path
    @font_path.setter
    def font_path(self, v): self._ensure_primary_text().font_path = v
    
    @property
    def text_height(self): return self._ensure_primary_text().size
    @text_height.setter
    def text_height(self, v): self._ensure_primary_text().size = v
    
    @property
    def text_depth(self): return self._ensure_primary_text().depth
    @text_depth.setter
    def text_depth(self, v): self._ensure_primary_text().depth = v
    
    @property
    def text_offset_x(self): return self._ensure_primary_text().offset_x
    @text_offset_x.setter
    def text_offset_x(self, v): self._ensure_primary_text().offset_x = v
    
    @property
    def text_offset_y(self): return self._ensure_primary_text().offset_y
    @text_offset_y.setter
    def text_offset_y(self, v): self._ensure_primary_text().offset_y = v

    @property
    def text_stroke_width(self): return self._ensure_primary_text().stroke_width
    @text_stroke_width.setter
    def text_stroke_width(self, v): self._ensure_primary_text().stroke_width = v

    @property
    def text_bold(self): return getattr(self._ensure_primary_text(), 'bold', False)
    @text_bold.setter
    def text_bold(self, v): setattr(self._ensure_primary_text(), 'bold', bool(v))

    @property
    def text_italic(self): return getattr(self._ensure_primary_text(), 'italic', False)
    @text_italic.setter
    def text_italic(self, v): setattr(self._ensure_primary_text(), 'italic', bool(v))

    @property
    def text_underline(self): return getattr(self._ensure_primary_text(), 'underline', False)
    @text_underline.setter
    def text_underline(self, v): setattr(self._ensure_primary_text(), 'underline', bool(v))

    def validate(self) -> tuple[bool, str]:
        # 验证几何参数
        geo_valid, geo_msg = self.geometry.validate()
        if not geo_valid:
            return False, geo_msg
            
        # 验证所有文字参数
        for idx, item in enumerate(self.text_items):
            t_valid, t_msg = item.validate()
            if not t_valid:
                return False, f"文字 #{idx+1} 错误: {t_msg}"
        # 验证所有图片参数
        for idx, item in enumerate(self.image_items):
            i_valid, i_msg = item.validate()
            if not i_valid:
                return False, f"图片 #{idx+1} 错误: {i_msg}"
        return True, ""


# 为了兼容旧代码，将 KeycapParameters 指向 KeycapDesign
KeycapParameters = KeycapDesign
