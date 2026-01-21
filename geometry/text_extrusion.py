"""
文字挤出处理
将2D字体轮廓转换为3D模型
"""
import cadquery as cq
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np
from geometry.font_processor import extract_glyph_outline, scale_and_center_geometry
from core.parameters import KeycapParameters, TextParameters


class TextExtrusion:
    """文字挤出生成器"""
    
    def __init__(self, params: KeycapParameters):
        self.params = params
    
    def create_text_model(self, text: str = None, font_size: float = None) -> cq.Workplane:
        """
        创建单个文字的基础3D模型（位于原点0,0）
        
        参数:
            text: 文字内容
            font_size: 文字大小 (mm)
        """
        target_text = text if text is not None else self.params.letter
        target_size = font_size if font_size is not None else self.params.text_height
        
        if not self.params.font_path or not target_text:
            return None
        
        # 提取字体轮廓
        geometry, bounds = extract_glyph_outline(
            self.params.font_path, 
            target_text
        )
        
        if geometry is None:
            return None
        
        # 计算参考宽度（用于缩放限制）
        text_ref_width = self.params.key_width * 0.8 # 稍微放宽限制
        
        # 缩放和居中
        geometry, bounds = scale_and_center_geometry(
            geometry, text_ref_width, target_size, bounds
        )
        
        if geometry is None:
            return None
        
        # 转换为CadQuery Workplane
        wp = self._geometry_to_sketch(geometry)
        
        if wp is None:
            return None
        
        # 挤出为3D模型
        text_depth = abs(self.params.text_depth)
        
        if self.params.text_depth > 0:
            # 凹陷文字（向下挤出）
            text_model = wp.extrude(-text_depth)
        else:
            # 凸起文字（向上挤出）
            text_model = wp.extrude(text_depth)
            
        # 注意：这里不再进行任何平移，返回的模型中心就在 (0,0)
        return text_model

    def generate_text_model(self) -> cq.Workplane:
        """
        生成完整的文字3D模型（包含所有字符，已定位并合并）
        
        返回:
            CadQuery Workplane对象
        """
        models = []
        
        # 确定要生成的文字列表
        items = self.params.text_items
        if not items:
            # 兼容模式：如果没有 text_items，尝试使用 params 的兼容属性创建默认项
            default_item = TextParameters(
                text=self.params.letter,
                size=self.params.text_height,
                offset_x=self.params.text_offset_x,
                offset_y=self.params.text_offset_y,
                depth=self.params.text_depth,
                font_path=self.params.font_path  # 重要：必须设置字体路径
            )
            items = [default_item]
            
        for item in items:
             # 支持 TextParameters 对象或字典（向前兼容）
             if isinstance(item, dict):
                 txt = item.get('text', self.params.letter)
                 x = item.get('x', 0.0)
                 y = item.get('y', 0.0)
                 sz = item.get('size', self.params.text_height)
                 font_path = item.get('font', self.params.font_path)
             else:
                 # 假设是 TextParameters 对象
                 txt = item.text
                 x = item.offset_x
                 y = item.offset_y
                 sz = item.size
                 font_path = item.font_path if item.font_path else self.params.font_path
             
             # 临时设置字体路径（如果 item 有自己的字体）
             original_font = self.params.font_path
             if font_path:
                 self.params.font_path = font_path
             
             tm = self.create_text_model(text=txt, font_size=sz)
             
             # 恢复原始字体路径
             self.params.font_path = original_font
             
             if tm:
                 # 将文字移动到其指定位置 (X, Y)
                 tm = tm.translate((x, y, 0))
                 models.append(tm)

        if not models:
            return None
        
        # 合并所有文字模型
        result = models[0]
        for m in models[1:]:
             result = result.union(m)
             
        return result
    
    def _geometry_to_sketch(self, geometry) -> cq.Workplane:
        """
        将shapely几何图形转换为CadQuery Workplane
        """
        try:
            # 创建唯一的Workplane
            wp = cq.Workplane("XY")
            
            # 定义绘制单个Polygon的内部函数
            def draw_polygon_on_wp(poly):
                # 绘制外环
                exterior = list(poly.exterior.coords)
                points = [(x, y) for x, y in exterior[:-1]]
                if len(points) >= 3:
                    wp.polyline(points).close()
                
                # 绘制内环（孔洞）
                for interior in poly.interiors:
                    interior_points = [(x, y) for x, y in interior.coords[:-1]]
                    if len(interior_points) >= 3:
                        wp.polyline(interior_points).close()
            
            # 处理几何体
            if isinstance(geometry, Polygon):
                draw_polygon_on_wp(geometry)
            elif isinstance(geometry, MultiPolygon):
                for poly in geometry.geoms:
                    draw_polygon_on_wp(poly)
            else:
                return None
                
            return wp
                
        except Exception as e:
            print(f"转换几何图形时出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _polygon_to_sketch(self, polygon: Polygon) -> cq.Workplane:
        """已废弃"""
        pass
    
    def apply_text_to_keycap(self, keycap: cq.Workplane) -> tuple:
        """
        将文字应用到按键顶面
        """
        # 生成已定位（XY）的组合文字模型
        text_model = self.generate_text_model()
        
        if text_model is None:
            print("警告：文字模型生成失败")
            return keycap, None
            
        # 获取几何参数
        top_thickness = self.params.top_thickness
        top_surface_z = top_thickness # 假设顶面表面在Z=top_thickness
        
        # 文字位置：在顶面顶部下方
        top_surface_z = top_thickness
        
        text_depth = self.params.text_depth
        
        # 在这里只处理 Z 轴定位 (应用到 Keycap 高度)
        if text_depth > 0:
            # 凹陷：文字嵌入顶面
            embed_depth = min(text_depth, top_thickness * 0.9)
            
            # 文字模型原本在Z=0到-depth。
            # 我们需要把它提到顶面。
            # 顶面 Z=top_thickness.
            # 文字顶部应该在顶面表面（Z=top_thickness），底部在Z=top_thickness-embed_depth
            # 所以文字模型（其顶部在Z=0）需要向上平移 top_surface_z
            text_model = text_model.translate((0, 0, top_surface_z))
            
            try:
                keycap = keycap.cut(text_model)
                print(f"文字已嵌入顶面（凹陷，深度={embed_depth}mm）")
            except Exception as e:
                print(f"从顶面中减去文字时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            # 凸起：文字在顶面上方
            raise_height = abs(text_depth)
            # 文字模型原本在Z=0到+depth。
            # 我们需要把它提到顶面。
            # 顶面 Z=top_thickness.
            # 文字底部应该在顶面表面（Z=top_thickness），顶部在Z=top_thickness+raise_height
            # 所以文字模型（其底部在Z=0）需要向上平移 top_surface_z
            text_model = text_model.translate((0, 0, top_surface_z))
            
            # 将文字模型与按键模型合并
            try:
                keycap = keycap.union(text_model)
                print(f"文字已生成（凸起，高度={raise_height}mm）")
            except Exception as e:
                print(f"将文字模型与按键合并时出错: {e}")
                import traceback
                traceback.print_exc()
        
        return keycap, text_model
