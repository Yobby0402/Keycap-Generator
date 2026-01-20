"""
STL文件导出
"""
import cadquery as cq
from pathlib import Path
from utils.file_utils import ensure_directory


def export_stl(model: cq.Workplane, filepath: str, ascii: bool = False) -> bool:
    """
    导出模型为STL文件
    
    参数:
        model: CadQuery Workplane对象
        filepath: 输出文件路径
        ascii: 是否使用ASCII格式（默认False，使用二进制格式）
    
    返回:
        是否成功
    """
    try:
        if model is None:
            return False
        
        # 确保目录存在
        ensure_directory(str(Path(filepath).parent))
        
        # 导出STL
        cq.exporters.export(model, filepath)
        
        return True
    except Exception as e:
        print(f"导出STL文件时出错: {e}")
        return False


def export_keycap_and_text(keycap_model: cq.Workplane, 
                           text_model: cq.Workplane,
                           base_path: str) -> tuple[bool, bool]:
    """
    分别导出按键和文字模型（为了多色打印，必须保持为两个独立文件）
    
    参数:
        keycap_model: 按键模型
        text_model: 文字模型
        base_path: 基础路径（不含扩展名）
    
    返回:
        (按键导出是否成功, 文字导出是否成功)
    """
    keycap_path = f"{base_path}_keycap.stl"
    text_path = f"{base_path}_text.stl"
    
    keycap_success = export_stl(keycap_model, keycap_path) if keycap_model else False
    text_success = export_stl(text_model, text_path) if text_model else False
    
    return keycap_success, text_success
