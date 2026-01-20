"""
文字挤出处理
将2D字体轮廓转换为3D模型
"""
import cadquery as cq
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np
from geometry.font_processor import extract_glyph_outline, scale_and_center_geometry
from core.parameters import KeycapParameters


class TextExtrusion:
    """文字挤出生成器"""
    
    def __init__(self, params: KeycapParameters):
        self.params = params
    
    def generate_text_model(self) -> cq.Workplane:
        """
        生成文字3D模型
        
        返回:
            CadQuery Workplane对象，如果生成失败返回None
        """
        if not self.params.font_path or not self.params.letter:
            return None
        
        # 提取字体轮廓
        geometry, bounds = extract_glyph_outline(
            self.params.font_path, 
            self.params.letter
        )
        
        if geometry is None:
            return None
        
        # 计算文字尺寸（基于按键尺寸的百分比）
        # 文字宽度和高度约为按键的60%
        text_width = self.params.key_width * 0.6
        text_height = self.params.text_height
        
        # 缩放和居中
        geometry, bounds = scale_and_center_geometry(
            geometry, text_width, text_height, bounds
        )
        
        if geometry is None:
            return None
        
        # 转换为CadQuery Workplane
        wp = self._geometry_to_sketch(geometry)
        
        if wp is None:
            return None
        
        # 挤出为3D模型
        # 文字应该从顶面表面（Z=top_thickness）开始，向下或向上挤出
        # 但为了后续处理方便，先从Z=0开始生成，然后在apply_text_to_keycap中移动到正确位置
        text_depth = abs(self.params.text_depth)
        
        if self.params.text_depth > 0:
            # 凹陷文字（向下挤出）
            text_model = wp.extrude(-text_depth)
        else:
            # 凸起文字（向上挤出）
            text_model = wp.extrude(text_depth)
        
        # 应用偏移（X, Y方向）
        if self.params.text_offset_x != 0 or self.params.text_offset_y != 0:
            text_model = text_model.translate((
                self.params.text_offset_x,
                self.params.text_offset_y,
                0  # Z方向偏移在apply_text_to_keycap中处理
            ))
        
        return text_model
    
    def _geometry_to_sketch(self, geometry) -> cq.Workplane:
        """
        将shapely几何图形转换为CadQuery Workplane
        
        参数:
            geometry: shapely几何图形
        
        返回:
            CadQuery Workplane对象
        """
        try:
            # 处理Polygon
            if isinstance(geometry, Polygon):
                return self._polygon_to_sketch(geometry)
            
            # 处理MultiPolygon
            elif isinstance(geometry, MultiPolygon):
                wp = None
                for poly in geometry.geoms:
                    poly_wp = self._polygon_to_sketch(poly)
                    if poly_wp is not None:
                        if wp is None:
                            wp = poly_wp
                        else:
                            # 合并多个多边形
                            wp = wp.union(poly_wp)
                return wp
            
            else:
                return None
                
        except Exception as e:
            print(f"转换几何图形时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _polygon_to_sketch(self, polygon: Polygon) -> cq.Workplane:
        """
        将单个Polygon转换为CadQuery Workplane
        使用更直接的方法：创建2D草图然后转换为Workplane
        """
        try:
            # 获取外环坐标
            exterior = list(polygon.exterior.coords)
            
            # 去掉最后一个重复点
            points = [(x, y) for x, y in exterior[:-1]]
            
            if len(points) < 3:
                return None
            
            # 创建Workplane并绘制多边形
            wp = cq.Workplane("XY")
            
            # 移动到第一个点
            wp = wp.moveTo(points[0][0], points[0][1])
            
            # 连接到其他点
            for point in points[1:]:
                wp = wp.lineTo(point[0], point[1])
            
            # 闭合
            wp = wp.close()
            
            # 处理内环（孔洞）- 从外环中减去
            for interior in polygon.interiors:
                interior_points = [(x, y) for x, y in interior.coords[:-1]]
                if len(interior_points) >= 3:
                    # 创建内环并减去
                    inner_wp = cq.Workplane("XY")
                    inner_wp = inner_wp.moveTo(interior_points[0][0], interior_points[0][1])
                    for point in interior_points[1:]:
                        inner_wp = inner_wp.lineTo(point[0], point[1])
                    inner_wp = inner_wp.close()
                    wp = wp.cut(inner_wp)
            
            return wp
            
        except Exception as e:
            print(f"转换Polygon时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def apply_text_to_keycap(self, keycap: cq.Workplane) -> tuple:
        """
        将文字应用到按键顶面
        
        文字位于顶面（Z=0），可以选择嵌入深度
        无论嵌入深度如何，文字都应该可见（不会完全没入顶面）
        
        参数:
            keycap: 按键模型（顶面在Z=0到Z=-top_thickness）
        
        返回:
            (修改后的按键模型, 文字模型)
        """
        text_model = self.generate_text_model()
        
        if text_model is None:
            print("警告：文字模型生成失败")
            return keycap, None
        
        # 顶面在Z=0到Z=top_thickness，顶面表面在Z=top_thickness
        top_surface_z = self.params.top_thickness  # 顶面表面（顶部）
        top_thickness = self.params.top_thickness
        
        # 应用文字偏移（X, Y方向）
        offset_x = self.params.text_offset_x
        offset_y = self.params.text_offset_y
        
        # 文字嵌入深度（正值为凹陷，负值为凸起）
        text_depth = self.params.text_depth
        
        # 将文字模型移动到顶面
        # 关键：文字必须与顶面在同一层（Z=top_thickness）
        # 顶面在Z=0到Z=top_thickness，顶面表面在Z=top_thickness
        # 文字应该从顶面表面（Z=top_thickness）开始，向下嵌入或向上凸起
        
        if text_depth > 0:
            # 凹陷：文字嵌入顶面
            # 确保文字不会完全没入顶面（至少露出一点）
            embed_depth = min(text_depth, top_thickness * 0.9)  # 最多嵌入90%的顶面厚度
            
            # 文字位置：从顶面表面（Z=top_thickness）向下嵌入
            # 文字模型从Z=0开始，向下挤出到Z=-embed_depth
            # 需要移动到：顶面表面（Z=top_thickness）向下embed_depth
            # 所以文字应该在Z=top_thickness-embed_depth到Z=top_thickness之间
            # 文字顶部应该在顶面表面（Z=top_thickness），底部在Z=top_thickness-embed_depth
            text_model = text_model.translate((
                offset_x,
                offset_y,
                top_surface_z  # 文字顶部对齐到顶面表面（Z=top_thickness）
            ))
            
            # 从顶面中减去文字（创建凹陷）
            # 注意：文字现在从Z=top_thickness向下延伸到Z=top_thickness-embed_depth
            # 顶面在Z=0到Z=top_thickness，所以文字会嵌入顶面
            try:
                keycap = keycap.cut(text_model)
                print(f"文字已嵌入顶面（凹陷，深度={embed_depth}mm，顶面厚度={top_thickness}mm）")
            except Exception as e:
                print(f"从顶面中减去文字时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            # 凸起：文字在顶面上方
            # 文字从顶面表面（Z=top_thickness）向上凸起
            raise_height = abs(text_depth)
            # 文字模型从Z=0开始，向上挤出到Z=raise_height
            # 需要移动到：顶面表面（Z=top_thickness）向上raise_height
            # 所以文字应该在Z=top_thickness到Z=top_thickness+raise_height之间
            text_model = text_model.translate((
                offset_x,
                offset_y,
                top_surface_z  # 文字底部对齐到顶面表面（Z=top_thickness）
            ))
            print(f"文字已生成（凸起，高度={raise_height}mm）")
        
        return keycap, text_model
