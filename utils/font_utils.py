"""
字体工具函数
"""
import os
from utils.file_utils import get_system_fonts, get_font_name


def find_times_new_roman() -> str:
    """
    查找Times New Roman字体路径
    
    返回:
        字体文件路径，如果找不到则返回None
    """
    # Times New Roman的常见文件名
    times_names = [
        "times.ttf", "timesi.ttf", "timesbd.ttf", "timesbi.ttf",
        "times new roman.ttf", "times new roman.ttc",
        "TIMES.TTF", "TIMESI.TTF", "TIMESBD.TTF", "TIMESBI.TTF"
    ]
    
    # 首先尝试从系统字体中查找
    try:
        fonts = get_system_fonts()
        for font_path in fonts:
            font_name = get_font_name(font_path).lower()
            if "times new roman" in font_name or "times" in font_name:
                # 验证是否是Times New Roman
                filename = os.path.basename(font_path).lower()
                if any(name in filename for name in times_names):
                    return font_path
    except Exception as e:
        print(f"查找Times New Roman字体时出错: {e}")
    
    # 如果找不到，尝试直接查找Windows字体目录
    if os.name == 'nt':
        font_dirs = [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'),
        ]
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for filename in times_names:
                    font_path = os.path.join(font_dir, filename)
                    if os.path.exists(font_path):
                        return font_path
                    # 尝试大小写变体
                    font_path_upper = os.path.join(font_dir, filename.upper())
                    if os.path.exists(font_path_upper):
                        return font_path_upper
    
    return None
