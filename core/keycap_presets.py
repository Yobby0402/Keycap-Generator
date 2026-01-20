"""
键帽预设数据
包含标准按键尺寸和键帽高度预设
"""

# 标准按键单位：1u = 19.05mm（标准键距）
U_UNIT_MM = 19.05

# 标准按键尺寸（宽度x高度，单位：u）
STANDARD_KEY_SIZES = {
    "1u": (1.0, 1.0),
    "1.25u": (1.25, 1.0),
    "1.5u": (1.5, 1.0),
    "1.75u": (1.75, 1.0),
    "2u": (2.0, 1.0),
    "2.25u": (2.25, 1.0),
    "2.5u": (2.5, 1.0),
    "2.75u": (2.75, 1.0),
    "3u": (3.0, 1.0),
    "6u": (6.0, 1.0),  # 空格键
    "6.25u": (6.25, 1.0),  # 标准空格键
    "7u": (7.0, 1.0),
    "2u_vertical": (1.0, 2.0),  # 垂直2u（如Enter键）
    "2.25u_vertical": (1.0, 2.25),
    "2.75u_vertical": (1.0, 2.75),
}

# 键帽高度预设（不同行的高度，单位：mm）
# 数据来源：机械键盘键帽高度标准
KEYCAP_HEIGHT_PROFILES = {
    "原厂高度": {
        "R1": 8.0,  # 功能键行
        "R2": 7.5,  # 数字键行
        "R3": 7.0,  # 主键区
        "R4": 6.5,  # 空格键行
    },
    "Cherry高度": {
        "R1": 8.0,
        "R2": 7.5,
        "R3": 7.0,
        "R4": 6.5,
    },
    "OEM高度": {
        "R1": 9.5,
        "R2": 8.5,
        "R3": 7.5,
        "R4": 6.5,
    },
    "SA高度": {
        "R1": 11.5,
        "R2": 11.0,
        "R3": 10.5,
        "R4": 10.0,
    },
    "DSA高度": {
        "R1": 7.0,  # 所有行相同（统一高度）
        "R2": 7.0,
        "R3": 7.0,
        "R4": 7.0,
    },
    "XDA高度": {
        "R1": 8.0,  # 所有行相同
        "R2": 8.0,
        "R3": 8.0,
        "R4": 8.0,
    },
}

# 预设位置（9宫格位置）
PRESET_POSITIONS = {
    "左上": (0, 0),
    "中上": (0, 0),
    "右上": (0, 0),
    "左中": (0, 0),
    "中间": (0, 0),
    "右中": (0, 0),
    "左下": (0, 0),
    "中下": (0, 0),
    "右下": (0, 0),
}


def u_to_mm(u_value: float) -> float:
    """将u单位转换为毫米"""
    return u_value * U_UNIT_MM


def mm_to_u(mm_value: float) -> float:
    """将毫米转换为u单位"""
    return mm_value / U_UNIT_MM


def get_key_size_mm(size_name: str) -> tuple[float, float]:
    """
    获取标准按键尺寸（毫米）
    
    参数:
        size_name: 尺寸名称，如 "1u", "1.25u" 等
    
    返回:
        (宽度, 高度) 单位：毫米
    """
    if size_name in STANDARD_KEY_SIZES:
        width_u, height_u = STANDARD_KEY_SIZES[size_name]
        return (u_to_mm(width_u), u_to_mm(height_u))
    return (u_to_mm(1.0), u_to_mm(1.0))  # 默认1u


def get_keycap_height(profile_name: str, row: str = "R3") -> float:
    """
    获取键帽高度
    
    参数:
        profile_name: 高度预设名称
        row: 行号 (R1, R2, R3, R4)
    
    返回:
        高度（毫米）
    """
    if profile_name in KEYCAP_HEIGHT_PROFILES:
        profile = KEYCAP_HEIGHT_PROFILES[profile_name]
        return profile.get(row, profile.get("R3", 7.0))
    return 7.0  # 默认高度
