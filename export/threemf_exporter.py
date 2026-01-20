"""
3MF文件导出
支持多材质/多颜色对象
"""
import cadquery as cq
from pathlib import Path
from utils.file_utils import ensure_directory


def export_3mf(keycap_model: cq.Workplane, 
               text_model: cq.Workplane,
               filepath: str) -> bool:
    """
    导出模型为3MF文件（支持多材质）
    
    参数:
        keycap_model: 按键模型
        text_model: 文字模型
        filepath: 输出文件路径
    
    返回:
        是否成功
    """
    try:
        import trimesh
        import tempfile
        import os as os_module
        
        if keycap_model is None:
            return False
        
        # 确保目录存在
        ensure_directory(str(Path(filepath).parent))
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            meshes = []
            names = []
            colors = []
            
            # 处理按键主体
            if keycap_model:
                keycap_tmp = os_module.path.join(tmpdir, "keycap.stl")
                # 使用CadQuery的导出功能
                cq.exporters.export(keycap_model, keycap_tmp)
                keycap_mesh = trimesh.load(keycap_tmp)
                meshes.append(keycap_mesh)
                names.append("Keycap")
                colors.append([64, 64, 64, 255])  # 深灰色
            
            # 处理文字部分
            if text_model:
                text_tmp = os_module.path.join(tmpdir, "text.stl")
                cq.exporters.export(text_model, text_tmp)
                text_mesh = trimesh.load(text_tmp)
                meshes.append(text_mesh)
                names.append("Text")
                colors.append([255, 255, 255, 255])  # 白色
            
            # 创建场景并设置颜色
            scene = trimesh.Scene()
            for mesh, name, color in zip(meshes, names, colors):
                # 设置顶点颜色
                mesh.visual.vertex_colors = color
                scene.add_geometry(mesh, node_name=name)
            
            # 导出为3MF
            scene.export(filepath, file_type='3mf')
        
        print(f"3MF文件已成功导出: {filepath}")
        return True
        
    except ImportError as e:
        print("错误: 需要安装 trimesh 库才能导出3MF格式")
        print("请运行: pip install trimesh")
        return False
    except Exception as e:
        print(f"导出3MF文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

