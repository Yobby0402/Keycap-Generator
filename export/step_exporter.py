"""
STEP文件导出
"""
import cadquery as cq
from pathlib import Path
from utils.file_utils import ensure_directory


def export_step(model: cq.Workplane, filepath: str) -> bool:
    """
    导出模型为STEP文件
    
    参数:
        model: CadQuery Workplane对象
        filepath: 输出文件路径
    
    返回:
        是否成功
    """
    try:
        if model is None:
            return False
        
        # 确保目录存在
        ensure_directory(str(Path(filepath).parent))
        
        # 导出STEP
        cq.exporters.export(model, filepath)
        
        return True
    except Exception as e:
        print(f"导出STEP文件时出错: {e}")
        return False


def export_keycap_and_text(keycap_model: cq.Workplane, 
                           text_model: cq.Workplane,
                           base_path: str) -> tuple[bool, bool]:
    """
    分别导出按键和文字模型
    """
    keycap_path = f"{base_path}_keycap.step"
    text_path = f"{base_path}_text.step"
    
    keycap_success = export_step(keycap_model, keycap_path) if keycap_model else False
    text_success = export_step(text_model, text_path) if text_model else False
    
    return keycap_success, text_success
