"""
参数管理类
定义和管理按键模型的所有参数
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class KeycapParameters:
    """按键参数类"""
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
    top_angle: float = 0.0       # 顶部斜角
    side_angle: float = 0.0      # 侧面斜角
    
    # 结构参数 (mm)
    wall_thickness: float = 1.0   # 壁厚（侧面厚度）
    top_thickness: float = 1.0   # 顶面厚度
    
    # 轴体类型
    stem_type: str = "MX"        # 轴体类型: MX, Alps等
    
    # 连接器参数
    stem_enabled: bool = True    # 是否生成连接器
    stem_height: float = 4.0     # 连接器深度 (mm)
    stem_cylinder_diameter: float = 5.4  # 圆柱直径 (mm)
    stem_cross_width: float = 1.0  # 十字宽度 (mm)
    stem_cross_length: float = 4.0  # 十字长度 (mm)
    
    # 字体和文字参数
    font_path: Optional[str] = None  # 字体文件路径
    letter: str = "A"            # 字母/字符
    text_height: float = 3.0     # 文字高度 (mm)
    text_depth: float = 0.5      # 文字深度 (mm) - 正值为凹陷，负值为凸起
    text_offset_x: float = 0.0   # 文字X偏移 (mm)
    text_offset_y: float = 0.0   # 文字Y偏移 (mm)
    
    # 圆角参数 (mm)
    corner_radius: float = 0.5   # 圆角半径
    
    def validate(self) -> tuple[bool, str]:
        """
        验证参数是否合理
        返回: (是否有效, 错误信息)
        """
        if self.key_width <= 0 or self.key_height <= 0 or self.key_depth <= 0:
            return False, "按键尺寸必须大于0"
        
        if self.wall_thickness <= 0:
            return False, "壁厚必须大于0"
        
        if self.top_angle < 0 or self.top_angle > 45:
            return False, "顶部斜角必须在0-45度之间"
        
        if self.side_angle < 0 or self.side_angle > 30:
            return False, "侧面斜角必须在0-30度之间"
        
        if not self.letter:
            return False, "字母不能为空"
        
        if self.text_height <= 0:
            return False, "文字高度必须大于0"
        
        return True, ""
