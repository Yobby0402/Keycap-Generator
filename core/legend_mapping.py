"""
KLE 图例位置映射
将 KLE 的 12 个位置索引映射到字符参数
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from core.parameters import TextParameters
from utils.font_utils import find_times_new_roman

# KLE 位置索引定义
# 顶面：左上0, 中上8, 右上2, 左中6, 正中9, 右中7, 左下1, 中下10, 右下3
# 侧刻：左侧4, 中间11, 右侧5
KLE_POSITION_NAMES = {
    0: "左上", 8: "中上", 2: "右上",
    6: "左中", 9: "正中", 7: "右中",
    1: "左下", 10: "中下", 3: "右下",
    4: "左侧(侧刻)", 11: "中间(侧刻)", 5: "右侧(侧刻)"
}

@dataclass
class LegendStyle:
    """字符样式配置"""
    font_path: Optional[str] = None
    size: float = 3.0  # mm
    offset_x: float = 0.0  # mm (相对于位置对齐后的偏移)
    offset_y: float = 0.0  # mm
    depth: float = 0.5  # mm (正值为凹陷，负值为凸起)
    rotation: float = 0.0  # 度


@dataclass
class LegendMapping:
    """图例映射配置 - 定义 KLE 位置索引到字符样式的映射"""
    # 映射表：{KLE位置索引: LegendStyle}
    mapping: Dict[int, LegendStyle] = field(default_factory=dict)
    
    def get_style(self, position_index: int, default_font_path: Optional[str] = None) -> LegendStyle:
        """
        获取指定位置的样式
        
        参数:
            position_index: KLE 位置索引 (0-11)
            default_font_path: 默认字体路径（如果样式中没有指定）
        
        返回:
            LegendStyle 对象
        """
        if position_index in self.mapping:
            style = self.mapping[position_index]
            # 如果样式没有字体路径，使用默认值
            if style.font_path is None:
                style = LegendStyle(
                    font_path=default_font_path,
                    size=style.size,
                    offset_x=style.offset_x,
                    offset_y=style.offset_y,
                    depth=style.depth,
                    rotation=style.rotation
                )
            return style
        else:
            # 返回默认样式
            return LegendStyle(font_path=default_font_path)
    
    def set_style(self, position_index: int, style: LegendStyle):
        """设置指定位置的样式"""
        self.mapping[position_index] = style
    
    @staticmethod
    def create_default() -> 'LegendMapping':
        """创建默认映射配置"""
        mapping = LegendMapping()
        
        # 查找Times New Roman作为默认字体
        default_font_path = find_times_new_roman()
        if default_font_path:
            print(f"使用默认字体: {default_font_path}")
        else:
            print("警告: 未找到Times New Roman字体，将使用None（可能导致文字生成失败）")
        
        # 默认配置：主要位置使用较大的字体，次要位置使用较小的字体
        # 顶面主要字符（正中）
        mapping.set_style(9, LegendStyle(font_path=default_font_path, size=5.0, offset_x=0.0, offset_y=0.0))
        
        # 顶面次要字符（左上、右上等）
        # 注意：offset是相对于base_position的偏移，base_position已经将字符放在了正确位置
        # 所以offset应该接近0，只用于微调
        mapping.set_style(0, LegendStyle(font_path=default_font_path, size=3.0, offset_x=0.0, offset_y=0.0))  # 左上
        mapping.set_style(2, LegendStyle(font_path=default_font_path, size=3.0, offset_x=0.0, offset_y=0.0))   # 右上
        mapping.set_style(8, LegendStyle(font_path=default_font_path, size=3.0, offset_x=0.0, offset_y=0.0))     # 中上
        
        # 侧刻（较小）
        mapping.set_style(4, LegendStyle(font_path=default_font_path, size=2.5, offset_x=-8.0, offset_y=0.0))   # 左侧
        mapping.set_style(11, LegendStyle(font_path=default_font_path, size=2.5, offset_x=0.0, offset_y=0.0))   # 中间
        mapping.set_style(5, LegendStyle(font_path=default_font_path, size=2.5, offset_x=8.0, offset_y=0.0))      # 右侧
        
        return mapping


def convert_kle_label_to_text_params(
    label_text: str,
    position_index: int,
    legend_mapping: LegendMapping,
    default_font_path: Optional[str] = None,
    key_width: float = 18.0,
    key_height: float = 18.0
) -> Optional[TextParameters]:
    """
    将 KLE 标签转换为 TextParameters
    
    参数:
        label_text: 标签文本
        position_index: KLE 位置索引 (0-11)
        legend_mapping: 样式映射配置
        default_font_path: 默认字体路径
        key_width: 按键宽度 (mm)
        key_height: 按键高度 (mm)
    
    返回:
        TextParameters 对象，如果 label_text 为空则返回 None
    """
    if not label_text or not label_text.strip():
        return None
    
    # 获取样式
    style = legend_mapping.get_style(position_index, default_font_path)
    
    # 如果样式和默认字体都没有，尝试使用Times New Roman
    final_font_path = style.font_path or default_font_path
    if not final_font_path:
        final_font_path = find_times_new_roman()
    
    # 计算位置偏移（基于对齐方式）
    # KLE 位置对齐方式：
    # 0-左上, 8-中上, 2-右上, 6-左中, 9-正中, 7-右中, 1-左下, 10-中下, 3-右下
    # 4-左侧(侧刻), 11-中间(侧刻), 5-右侧(侧刻)
    
    base_x, base_y = _calculate_base_position(position_index, key_width, key_height)
    
    # 创建 TextParameters
    return TextParameters(
        text=label_text.strip(),
        font_path=final_font_path,
        size=style.size,
        depth=style.depth,
        offset_x=base_x + style.offset_x,
        offset_y=base_y + style.offset_y
    )


def _calculate_base_position(position_index: int, key_width: float, key_height: float) -> tuple[float, float]:
    """
    根据位置索引计算基础位置（对齐后的坐标）
    
    返回:
        (x, y) 坐标 (mm)，相对于按键中心
    """
    # 按键中心为 (0, 0)
    # 按键范围：x 从 -key_width/2 到 key_width/2
    #          y 从 -key_height/2 到 key_height/2
    
    half_w = key_width / 2
    half_h = key_height / 2
    
    # 位置映射（相对于中心）
    position_map = {
        0: (-half_w * 0.7, half_h * 0.7),    # 左上
        8: (0, half_h * 0.7),                # 中上
        2: (half_w * 0.7, half_h * 0.7),     # 右上
        6: (-half_w * 0.7, 0),               # 左中
        9: (0, 0),                            # 正中
        7: (half_w * 0.7, 0),                # 右中
        1: (-half_w * 0.7, -half_h * 0.7),   # 左下
        10: (0, -half_h * 0.7),              # 中下
        3: (half_w * 0.7, -half_h * 0.7), # 右下
        # 侧刻位置（显示在按键下方或侧面）
        4: (-half_w * 0.8, -half_h * 0.9),  # 左侧(侧刻)
        11: (0, -half_h * 0.9),              # 中间(侧刻)
        5: (half_w * 0.8, -half_h * 0.9),    # 右侧(侧刻)
    }
    
    return position_map.get(position_index, (0, 0))
