"""
字体轮廓处理
使用fontTools提取字体轮廓，转换为shapely几何图形
"""
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
import numpy as np


class ShapelyPen(BasePen):
    """将字体轮廓转换为shapely几何图形的Pen"""
    
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.polygons = []
        self.current_polygon = []
        self.start_point = None
    
    def _moveTo(self, pt):
        if self.current_polygon:
            if len(self.current_polygon) >= 3:
                try:
                    poly = Polygon(self.current_polygon)
                    if poly.is_valid:
                        self.polygons.append(poly)
                except:
                    pass
        self.current_polygon = [pt]
        self.start_point = pt
    
    def _lineTo(self, pt):
        self.current_polygon.append(pt)
    
    def _curveTo(self, *points):
        # 简单的线性近似，实际应该使用贝塞尔曲线
        if self.current_polygon:
            last_pt = self.current_polygon[-1]
            for pt in points:
                self.current_polygon.append(pt)
    
    def _qCurveTo(self, *points):
        # 二次贝塞尔曲线的线性近似
        if self.current_polygon:
            last_pt = self.current_polygon[-1]
            for pt in points:
                self.current_polygon.append(pt)
    
    def _closePath(self):
        if self.current_polygon and len(self.current_polygon) >= 3:
            # 确保闭合
            if self.current_polygon[0] != self.current_polygon[-1]:
                self.current_polygon.append(self.current_polygon[0])
            
            try:
                poly = Polygon(self.current_polygon)
                if poly.is_valid:
                    self.polygons.append(poly)
            except:
                pass
        self.current_polygon = []
    
    def get_geometry(self):
        """获取最终的几何图形"""
        # 处理最后一个多边形
        if self.current_polygon and len(self.current_polygon) >= 3:
            if self.current_polygon[0] != self.current_polygon[-1]:
                self.current_polygon.append(self.current_polygon[0])
            try:
                poly = Polygon(self.current_polygon)
                if poly.is_valid:
                    self.polygons.append(poly)
            except:
                pass
        
        if not self.polygons:
            return None
        
        if len(self.polygons) == 1:
            return self.polygons[0]
        else:
            # 合并多个多边形
            try:
                return unary_union(self.polygons)
            except:
                return MultiPolygon(self.polygons)


def extract_glyph_outline(font_path: str, character: str) -> tuple:
    """
    从字体文件提取字符轮廓
    
    参数:
        font_path: 字体文件路径
        character: 要提取的字符
    
    返回:
        (几何图形, 边界框) 或 (None, None)
    """
    try:
        font = TTFont(font_path)
        glyph_set = font.getGlyphSet()
        
        # 获取字符的glyph名称
        cmap = font.getBestCmap()
        if ord(character) not in cmap:
            return None, None
        
        glyph_name = cmap[ord(character)]
        glyph = glyph_set[glyph_name]
        
        # 使用ShapelyPen提取轮廓
        pen = ShapelyPen(glyph_set)
        glyph.draw(pen)
        
        geometry = pen.get_geometry()
        
        if geometry is None:
            return None, None
        
        # 获取边界框
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        
        return geometry, bounds
        
    except Exception as e:
        print(f"提取字体轮廓时出错: {e}")
        return None, None


def scale_and_center_geometry(geometry, target_width: float, target_height: float, 
                              bounds: tuple) -> tuple:
    """
    缩放和居中几何图形
    
    参数:
        geometry: shapely几何图形
        target_width: 目标宽度
        target_height: 目标高度
        bounds: 原始边界框 (minx, miny, maxx, maxy)
    
    返回:
        (缩放后的几何图形, 新的边界框)
    """
    if geometry is None or bounds is None:
        return None, None
    
    minx, miny, maxx, maxy = bounds
    current_width = maxx - minx
    current_height = maxy - miny
    
    if current_width == 0 or current_height == 0:
        return None, None
    
    # 计算缩放比例（保持宽高比）
    scale_x = target_width / current_width
    scale_y = target_height / current_height
    scale_factor = min(scale_x, scale_y)  # 使用较小的比例以保持宽高比
    
    # 计算中心点
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    
    # 先平移到原点，然后缩放，再平移回中心
    from shapely.affinity import translate, scale
    
    # 平移到原点
    geometry = translate(geometry, xoff=-center_x, yoff=-center_y)
    
    # 缩放
    geometry = scale(geometry, xfact=scale_factor, yfact=scale_factor, origin=(0, 0))
    
    # 计算新的边界框
    new_bounds = geometry.bounds
    new_width = new_bounds[2] - new_bounds[0]
    new_height = new_bounds[3] - new_bounds[1]
    
    return geometry, new_bounds
