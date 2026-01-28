"""
文件操作工具函数
"""
import os
from pathlib import Path


def ensure_directory(path: str) -> None:
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_system_fonts() -> list[str]:
    """
    获取系统字体列表
    返回字体文件路径列表
    """
    fonts = []
    
    # Windows字体路径
    if os.name == 'nt':
        font_dirs = [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts'),
        ]
    # Linux字体路径
    elif os.name == 'posix':
        font_dirs = [
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            os.path.expanduser('~/.fonts'),
        ]
    # macOS字体路径
    else:
        font_dirs = [
            '/Library/Fonts',
            '/System/Library/Fonts',
            os.path.expanduser('~/Library/Fonts'),
        ]
    
    # 支持的字体格式
    font_extensions = ['.ttf', '.otf', '.ttc']
    
    for font_dir in font_dirs:
        if os.path.exists(font_dir):
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in font_extensions):
                        font_path = os.path.join(root, file)
                        fonts.append(font_path)
    
    return sorted(set(fonts))


def get_font_name(font_path: str) -> str:
    """从字体文件路径提取字体名称；若有中文名则优先显示中文名"""
    try:
        from fontTools.ttLib import TTFont
        
        font = TTFont(font_path)
        name_table = font['name']
        
        # 候选列表 (score, text)
        candidates = []
        
        for record in name_table.names:
            if record.nameID not in [1, 16]:  # Family (1), Preferred Family (16)
                continue
            score = 0
            if record.nameID == 16:
                score += 100
            elif record.nameID == 1:
                score += 50
            if record.platformID == 3:  # Windows
                score += 20
            # 优先中文：简体(0x804)、繁体(0x404)，其次英语(0x409)
            if record.langID == 0x804:
                score += 15  # 简体中文
            elif record.langID == 0x404:
                score += 12  # 繁体中文
            elif record.langID == 0x409:
                score += 10  # 英语
            
            try:
                text = record.toUnicode()
                candidates.append((score, text))
            except Exception:
                continue
                
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
        return os.path.splitext(os.path.basename(font_path))[0]
    except Exception:
        return os.path.splitext(os.path.basename(font_path))[0]
