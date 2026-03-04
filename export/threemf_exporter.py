"""
3MF文件导出
支持多材质/多颜色对象；批量导出时按按键颜色区分
"""
import cadquery as cq
from pathlib import Path
from typing import List, Tuple, Optional
from utils.file_utils import ensure_directory


def _hex_to_rgba(hex_color: str) -> List[int]:
    """#RRGGBB -> [r,g,b,255]"""
    h = (hex_color or "#cccccc").lstrip("#")
    if len(h) == 6:
        return [int(h[i:i+2], 16) for i in (0, 2, 4)] + [255]
    return [204, 204, 204, 255]


def export_3mf(keycap_model: cq.Workplane,
               text_model: cq.Workplane,
               filepath: str,
               image_inlay: cq.Workplane = None) -> bool:
    """
    导出模型为3MF文件（支持多材质）

    参数:
        keycap_model: 按键模型
        text_model: 文字模型
        filepath: 输出文件路径
        image_inlay: 图片凹陷的镶嵌体（depth>0），用于双色打印

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

            # 处理图片镶嵌体（凹陷时填充用）
            if image_inlay is not None:
                inlay_tmp = os_module.path.join(tmpdir, "inlay.stl")
                cq.exporters.export(image_inlay, inlay_tmp)
                inlay_mesh = trimesh.load(inlay_tmp)
                meshes.append(inlay_mesh)
                names.append("Inlay")
                colors.append([230, 190, 50, 255])  # 金/黄色

            # 创建场景并设置颜色
            scene = trimesh.Scene()
            for mesh, name, color in zip(meshes, names, colors):
                mesh.visual.vertex_colors = color
                scene.add_geometry(mesh, node_name=name)

            # 导出为3MF
            scene.export(filepath, file_type='3mf')
        
        print(f"3MF文件已成功导出: {filepath}")
        return True
        
    except ImportError as e:
        err = str(e).strip()
        print("错误: 导出3MF需要 trimesh 及其依赖")
        print(f"  具体原因: {e}")
        if "networkx" in err:
            print("  解决方法: 在终端运行 pip install networkx")
        elif "lxml" in err:
            print("  解决方法: 在终端运行 pip install lxml")
        else:
            print("  解决方法: 在终端运行 pip install trimesh")
        print("  若使用打包的 exe，请用「python main.py」运行并安装上述依赖，或重新打包前先安装再打包。")
        return False
    except Exception as e:
        print(f"导出3MF文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def export_3mf_batch(
    items: List[Tuple[cq.Workplane, Optional[cq.Workplane], str, str]],
    filepath: str
) -> bool:
    """
    批量导出 3MF，同种 (key_color, text_color) 的键帽/文字分别合并为一个 mesh，
    便于在切片软件中按耗材种类批量设置。
    items: [(keycap_model, text_model, key_color_hex, text_color_hex), ...]
    """
    try:
        import trimesh
        import tempfile
        import os as os_module

        if not items:
            return False
        ensure_directory(str(Path(filepath).parent))

        # 按 (key_color, text_color) 分组
        groups: dict = {}  # (kc_hex, tc_hex) -> [(keycap_wp, text_wp), ...]
        for keycap_model, text_model, kc_hex, tc_hex in items:
            kc = kc_hex or "#cccccc"
            tc = tc_hex or "#000000"
            key = (kc, tc)
            if key not in groups:
                groups[key] = []
            groups[key].append((keycap_model, text_model))

        def _safe(s: str) -> str:
            return (s or "").replace("#", "_")

        with tempfile.TemporaryDirectory() as tmpdir:
            scene = trimesh.Scene()
            for (kc_hex, tc_hex), group_items in groups.items():
                kc_rgba = _hex_to_rgba(kc_hex)
                tc_rgba = _hex_to_rgba(tc_hex)
                sk, st = _safe(kc_hex), _safe(tc_hex)
                keycap_meshes = []
                text_meshes = []
                for idx, (keycap_model, text_model) in enumerate(group_items):
                    if keycap_model:
                        kp_tmp = os_module.path.join(tmpdir, f"kp_{sk}_{st}_{idx}.stl")
                        cq.exporters.export(keycap_model, kp_tmp)
                        keycap_meshes.append(trimesh.load(kp_tmp))
                    if text_model:
                        tx_tmp = os_module.path.join(tmpdir, f"tx_{sk}_{st}_{idx}.stl")
                        cq.exporters.export(text_model, tx_tmp)
                        text_meshes.append(trimesh.load(tx_tmp))
                if keycap_meshes:
                    merged_keycap = trimesh.util.concatenate(keycap_meshes)
                    merged_keycap.visual.vertex_colors = kc_rgba
                    scene.add_geometry(merged_keycap, node_name=f"Keycap_{sk}_{st}")
                if text_meshes:
                    merged_text = trimesh.util.concatenate(text_meshes)
                    merged_text.visual.vertex_colors = tc_rgba
                    scene.add_geometry(merged_text, node_name=f"Text_{sk}_{st}")
            scene.export(filepath, file_type='3mf')
        print(f"3MF 批量（同色已合并，便于按耗材设置）已导出: {filepath}")
        return True
    except ImportError as e:
        err = str(e).strip()
        print("错误: 导出3MF需要 trimesh 及其依赖")
        print(f"  具体原因: {e}")
        if "networkx" in err:
            print("  解决方法: pip install networkx")
        elif "lxml" in err:
            print("  解决方法: pip install lxml")
        else:
            print("  解决方法: pip install trimesh")
        return False
    except Exception as e:
        print(f"导出3MF批量时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

