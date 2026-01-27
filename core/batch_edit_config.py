"""
批量编辑配置
用于批量编辑同一类型按键的样式
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from core.key_type_analyzer import KeyTypeSignature
from core.parameters import KeycapGeometry
from core.legend_mapping import LegendStyle


@dataclass
class BatchEditConfig:
    """批量编辑配置"""
    key_type: KeyTypeSignature
    geometry: KeycapGeometry  # 几何参数（所有该类型按键共用）
    text_styles: Dict[int, LegendStyle] = field(default_factory=dict)  # 位置索引 -> 样式
    # 例如：{0: LegendStyle(size=3.0, ...), 9: LegendStyle(size=5.0, ...)}
    
    def get_style_for_position(self, position_index: int, default_font_path: Optional[str] = None) -> LegendStyle:
        """
        获取指定位置的样式
        
        参数:
            position_index: KLE 位置索引 (0-11)
            default_font_path: 默认字体路径
        
        返回:
            LegendStyle 对象
        """
        if position_index in self.text_styles:
            style = self.text_styles[position_index]
            # 如果样式没有字体路径，使用默认值
            if style.font_path is None:
                style = LegendStyle(
                    font_path=default_font_path,
                    size=style.size,
                    offset_x=style.offset_x,
                    offset_y=style.offset_y,
                    depth=style.depth,
                    rotation=style.rotation,
                    stroke_width=getattr(style, 'stroke_width', 0.0),
                    bold=getattr(style, 'bold', False),
                    italic=getattr(style, 'italic', False),
                    underline=getattr(style, 'underline', False)
                )
            return style
        else:
            # 返回默认样式
            return LegendStyle(font_path=default_font_path)
    
    def set_style_for_position(self, position_index: int, style: LegendStyle):
        """设置指定位置的样式"""
        self.text_styles[position_index] = style
