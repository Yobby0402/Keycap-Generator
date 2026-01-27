"""
图片挤出处理
将位图转换为轮廓并挤出为 3D 模型，支持凹陷/凸起
"""
import cadquery as cq
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from geometry.font_processor import scale_and_center_geometry


def _load_image_grayscale(path: str):
    """使用 OpenCV 加载图片为灰度；若失败则尝试 Pillow 转灰度再交 OpenCV。"""
    try:
        import cv2
        im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if im is not None:
            return im
    except Exception:
        pass
    try:
        from PIL import Image
        import cv2
        pil = Image.open(path).convert("L")
        return np.array(pil)
    except Exception as e:
        print(f"无法加载图片 {path}: {e}")
        return None


def _image_to_geometry(
    image_path: str,
    threshold: int = 128,
    invert: bool = False,
) -> tuple:
    """
    将图片二值化并提取轮廓，转为 Shapely 几何（多边形，y 轴向上）。
    返回 (geometry, bounds) 或 (None, None)。坐标单位为像素（y 已翻转）。
    """
    try:
        import cv2
    except ImportError:
        print("图片挤出需要 opencv-python，请安装: pip install opencv-python")
        return None, None

    gray = _load_image_grayscale(image_path)
    if gray is None:
        return None, None

    # 二值化：invert=False 时深色(低于 threshold)为 255，即凸起深色区域
    thresh_type = cv2.THRESH_BINARY_INV if not invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, threshold, 255, thresh_type)

    # 使用 RETR_CCOMP 获取层级，以区分外轮廓与内环（孔洞）
    contours, hierarchy = cv2.findContours(
        binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        print(f"图片 {image_path} 未提取到有效轮廓（可尝试调整阈值或 invert）")
        return None, None

    img_h = gray.shape[0]
    hier = hierarchy[0] if hierarchy is not None else None  # (N,4): [Next,Prev,First_Child,Parent]
    polygons = []

    for i, cnt in enumerate(contours):
        if cnt.shape[0] < 3:
            continue
        # 只处理顶层轮廓（Parent==-1）；其子轮廓作为内环
        if hier is not None and i < hier.shape[0] and int(hier[i][3]) != -1:
            continue
        # 外环：像素 (x,y) y 向下 -> 转为 y 向上
        ext_pts = [(float(x), float(img_h - 1 - y)) for x, y in cnt.reshape(-1, 2)]
        holes_list = []
        if hier is not None:
            for j in range(len(contours)):
                if j >= hier.shape[0]:
                    break
                if int(hier[j][3]) != i or contours[j].shape[0] < 3:
                    continue
                hpts = [(float(x), float(img_h - 1 - y)) for x, y in contours[j].reshape(-1, 2)]
                holes_list.append(hpts)
        try:
            if holes_list:
                poly = Polygon(shell=ext_pts, holes=holes_list)
            else:
                poly = Polygon(ext_pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
            if isinstance(poly, MultiPolygon):
                polygons.extend(poly.geoms)
            else:
                polygons.append(poly)
        except Exception as e:
            print(f"轮廓转 Polygon 失败: {e}")
            continue

    if not polygons:
        return None, None

    try:
        geom = unary_union(polygons)
    except Exception as e:
        print(f"合并轮廓失败: {e}")
        geom = polygons[0] if polygons else None

    if geom is None or geom.is_empty:
        return None, None

    return geom, geom.bounds


def _geometry_to_solid(geometry, depth_abs: float, depth_positive: bool) -> cq.Workplane:
    """
    将 Shapely 几何转为 CadQuery 实体：每个子多边形先按外环挤出，再用内环 cut 出孔洞，
    最后 union 所有块，保证完整填充且正确镂空。
    depth_positive: True=凹陷(向下挤出)，False=凸起(向上挤出)
    """
    try:
        polys = [geometry] if isinstance(geometry, Polygon) else list(geometry.geoms)
        solids = []
        for poly in polys:
            ext = list(poly.exterior.coords)[:-1]
            if len(ext) < 3:
                continue
            pts = [(float(x), float(y)) for x, y in ext]
            wp = cq.Workplane("XY").polyline(pts).close()
            if depth_positive:
                s = wp.extrude(-depth_abs)
            else:
                s = wp.extrude(depth_abs)
            # 内环：从实体中 cut 出孔洞
            for interior in poly.interiors:
                ring = list(interior.coords)[:-1]
                if len(ring) < 3:
                    continue
                hp = [(float(x), float(y)) for x, y in ring]
                wh = cq.Workplane("XY").polyline(hp).close()
                if depth_positive:
                    hole_s = wh.extrude(-depth_abs)
                else:
                    hole_s = wh.extrude(depth_abs)
                try:
                    s = s.cut(hole_s)
                except Exception as e:
                    print(f"内环 cut 失败: {e}")
            solids.append(s)
        if not solids:
            return None
        out = solids[0]
        for s in solids[1:]:
            out = out.union(s)
        return out
    except Exception as e:
        print(f"几何转 CadQuery 实体失败: {e}")
        import traceback
        traceback.print_exc()
        return None


class ImageExtrusion:
    """图片挤出：从位图生成 3D 凸起/凹陷并应用到键帽顶面。"""

    def __init__(self, params):
        self.params = params

    def create_image_model(
        self,
        image_path: str,
        size_mm: float,
        depth: float,
        threshold: int = 128,
        invert: bool = False,
    ) -> cq.Workplane:
        """
        创建单张图片的 3D 挤出（位于原点，未做 offset）。
        参数:
            image_path: 图片路径
            size_mm: 键帽上的最大尺寸 (mm)
            depth: 挤出深度，>0 凹陷，<0 凸起
            threshold: 二值化阈值
            invert: 是否反转明暗
        返回:
            CadQuery Workplane 或 None
        """
        path = Path(image_path)
        if not path.is_file():
            print(f"图片不存在: {image_path}")
            return None

        geometry, bounds = _image_to_geometry(str(path), threshold=threshold, invert=invert)
        if geometry is None or bounds is None:
            return None

        # 缩放到 size_mm 为最大边，并居中
        target = size_mm
        geometry, _ = scale_and_center_geometry(geometry, target, target, bounds)
        if geometry is None:
            return None

        depth_abs = abs(depth)
        model = _geometry_to_solid(geometry, depth_abs, depth > 0)
        return model

    def apply_images_to_keycap(self, keycap: cq.Workplane) -> tuple:
        """
        将所有 image_items 应用到键帽顶面（先文字后图片时，在文字之后调用）。
        返回 (keycap, last_image_model, inlay)；
        若没有任何图片则返回 (keycap, None, None)。
        当 depth>0（凹陷）时，inlay 为可单独导出的镶嵌体，用于双色打印填充。
        """
        items = getattr(self.params, "image_items", None) or []
        if not items:
            return keycap, None, None

        top_z = getattr(self.params, "top_thickness", 1.0)
        last_model = None
        inlay_solids = []

        for item in items:
            # 兼容 dict 与 ImageParameters
            if isinstance(item, dict):
                path = item.get("path", "")
                depth = item.get("depth", 0.5)
                ox = item.get("offset_x", 0.0)
                oy = item.get("offset_y", 0.0)
                size = item.get("size", 6.0)
                scale = item.get("scale", 1.0) or 1.0
                thresh = item.get("threshold", 128)
                inv = item.get("invert", False)
            else:
                path = getattr(item, "path", "") or ""
                depth = getattr(item, "depth", 0.5)
                ox = getattr(item, "offset_x", 0.0)
                oy = getattr(item, "offset_y", 0.0)
                size = getattr(item, "size", 6.0)
                scale = getattr(item, "scale", 1.0) or 1.0
                thresh = getattr(item, "threshold", 128)
                inv = getattr(item, "invert", False)

            if not path or not Path(path).is_file():
                continue

            effective_size = size * scale
            model = self.create_image_model(path, effective_size, depth, threshold=thresh, invert=inv)
            if model is None:
                continue

            model = model.translate((ox, oy, 0))
            model = model.translate((0, 0, top_z))
            last_model = model

            try:
                if depth > 0:
                    inlay_solids.append(model)
                    keycap = keycap.cut(model)
                else:
                    keycap = keycap.union(model)
            except Exception as e:
                print(f"应用图片 {path} 到键帽失败: {e}")
                import traceback
                traceback.print_exc()

        inlay = None
        if inlay_solids:
            inlay = inlay_solids[0]
            for s in inlay_solids[1:]:
                inlay = inlay.union(s)
        return keycap, last_model, inlay
