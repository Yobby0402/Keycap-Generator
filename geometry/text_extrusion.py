"""
文字挤出处理
将2D字体轮廓转换为3D模型
支持线宽、加粗、斜体、下划线等样式
"""
import cadquery as cq
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from shapely.affinity import skew
from math import tan, radians
import numpy as np
from geometry.font_processor import extract_glyph_outline, scale_and_center_geometry
from core.parameters import KeycapParameters, TextParameters


class TextExtrusion:
    """文字挤出生成器"""
    
    def __init__(self, params: KeycapParameters):
        self.params = params
    
    def create_text_model(self, text: str = None, font_size: float = None, stroke_width: float = 0.0,
                          bold: bool = False, italic: bool = False, underline: bool = False) -> cq.Workplane:
        """
        创建单个文字的基础3D模型（位于原点0,0）
        
        参数:
            text: 文字内容
            font_size: 文字大小 (mm)
            stroke_width: 线宽/描边加粗 (mm)，>0 时向外扩展轮廓
            bold: 加粗（额外 0.15mm 描边）
            italic: 斜体（几何剪切约 12°）
            underline: 下划线
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
        text_ref_width = self.params.key_width * 0.8
        
        # 缩放和居中
        geometry, bounds = scale_and_center_geometry(
            geometry, text_ref_width, target_size, bounds
        )
        
        if geometry is None:
            return None
        
        # 斜体：几何剪切（约 12°）
        if italic:
            try:
                geometry = skew(geometry, xs=tan(radians(12)), origin='center')
                if geometry is None or (hasattr(geometry, 'is_empty') and geometry.is_empty):
                    geometry = None
            except Exception as e:
                print(f"斜体 skew 失败: {e}")
            if geometry is None:
                return None
        
        # 下划线：在轮廓下方加一条细矩形
        if underline:
            try:
                minx, miny, maxx, maxy = geometry.bounds
                h = maxy - miny
                thick = max(h * 0.08, 0.05)
                gap = h * 0.02
                ul_box = box(minx, miny - gap - thick, maxx, miny - gap)
                geometry = unary_union([geometry, ul_box])
            except Exception as e:
                print(f"下划线 失败: {e}")
        
        # 线宽/加粗：向外 buffer，加粗时额外 0.15mm
        effective_stroke = stroke_width + (0.15 if bold else 0.0)
        if effective_stroke > 0:
            try:
                geometry = geometry.buffer(effective_stroke / 2.0)
                if geometry is None or (hasattr(geometry, 'is_empty') and geometry.is_empty):
                    geometry = None
            except Exception as e:
                print(f"线宽 buffer 失败 (stroke_width={effective_stroke}): {e}")
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
            # 兼容模式：从 params 的「字体设置」取值（线宽、加粗、斜体、下划线）
            default_item = TextParameters(
                text=self.params.letter,
                size=self.params.text_height,
                offset_x=self.params.text_offset_x,
                offset_y=self.params.text_offset_y,
                depth=self.params.text_depth,
                font_path=self.params.font_path,
                stroke_width=getattr(self.params, 'text_stroke_width', 0.0),
                bold=getattr(self.params, 'text_bold', False),
                italic=getattr(self.params, 'text_italic', False),
                underline=getattr(self.params, 'text_underline', False)
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
                 stroke_width = item.get('stroke_width', 0.0)
                 bold = item.get('bold', False)
                 italic = item.get('italic', False)
                 underline = item.get('underline', False)
             else:
                 txt = item.text
                 x = item.offset_x
                 y = item.offset_y
                 sz = item.size
                 font_path = item.font_path if item.font_path else self.params.font_path
                 stroke_width = getattr(item, 'stroke_width', 0.0)
                 bold = getattr(item, 'bold', False)
                 italic = getattr(item, 'italic', False)
                 underline = getattr(item, 'underline', False)
             
             original_font = self.params.font_path
             if font_path:
                 self.params.font_path = font_path
             tm = self.create_text_model(text=txt, font_size=sz, stroke_width=stroke_width,
                                         bold=bold, italic=italic, underline=underline)
             
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
    
    def make_text_solid_for_curved(self, arc_height: float, is_convex: bool, top_thickness: float):
        """
        按“弧面切割”思路：生成足够高的文字立方体（顶面高度+字符高度/深度），
        后续用键帽+弧面体做 intersect 裁剪掉弧面以外的多余部分，使文字顶/底面贴合弧面。
        
        - 凹陷：足够高的向下柱体，保证贯穿弧面并向下 user_depth；裁剪后凹槽顶=弧面。
        - 凸起：从弧面表面向上的柱体；裁剪后底面贴合弧面。
        
        返回 (text_solid, is_recessed)。is_recessed=True 表示凹陷，False 表示凸起。
        """
        depth = self.params.text_depth
        eps = 0.5   # 放大余量，保证边缘处柱体也能完全穿透弧面，避免“边缘埋没”
        if depth > 0:
            # 凹陷：足够高的向下柱体，必须从弧面“最外/最高”处之上开始，贯穿到 user_depth 之下
            if is_convex and arc_height > 0:
                # 凸起弧面：柱顶在弧顶之上，向下贯穿弧面到 top_thickness-depth，余量稍大避免边缘处未穿透
                total_depth = arc_height + eps + depth
                top_z = top_thickness + arc_height + eps
            else:
                # 凹陷弧面：柱顶必须在碗口(rim)之上，向下贯穿整只碗再 user_depth，否则边缘不穿透、会埋没
                total_depth = arc_height + depth + eps
                top_z = top_thickness + eps
            old = self.params.text_depth
            self.params.text_depth = total_depth
            solid = self.generate_text_model()
            self.params.text_depth = old
            if solid is None:
                return None, True
            solid = solid.translate((0, 0, top_z))
            return solid, True
        else:
            # 凸起：从弧面表面向上挤出
            raise_h = abs(depth)
            bottom_z = top_thickness + arc_height if (is_convex and arc_height > 0) else (top_thickness - arc_height)
            old = self.params.text_depth
            self.params.text_depth = -raise_h  # 用负值表示凸起
            solid = self.generate_text_model()
            self.params.text_depth = old
            if solid is None:
                return None, False
            solid = solid.translate((0, 0, bottom_z))
            return solid, False
    
    def apply_text_to_keycap(self, keycap: cq.Workplane, curved_part_and_convex=None) -> tuple:
        """
        将文字应用到按键顶面。
        
        curved_part_and_convex: 若为 (curved_part, is_convex)，则在本方法内对弧面做文字布尔后再与 keycap 合并，
        使文字完全贴合弧面；否则按“无弧面”的平面顶面逻辑处理。
        """
        top_thickness = self.params.top_thickness
        text_depth = self.params.text_depth
        arc_height = self._calculate_arc_height_offset()
        
        # 若调用方传入弧面体：按“弧面切割”思路——先做足够高的文字立方体，再用键帽+弧面体做
        # intersect 裁剪掉弧面以外的多余部分，使文字顶/底面贴合弧面；先弧面与键帽合并/切割，再对文字做 intersect，最后 cut/union。
        if curved_part_and_convex is not None:
            curved_part, is_convex = curved_part_and_convex
            if curved_part is None:
                curved_part_and_convex = None  # 按无弧面处理
            else:
                text_solid, is_recessed = self.make_text_solid_for_curved(arc_height, is_convex, top_thickness)
                if text_solid is None:
                    return keycap, None
                try:
                    if is_recessed:
                        # 凹陷：先合并/切割弧面，再直接用文字柱体从键帽上 cut，不做 intersect。
                        # 用 intersect 再 cut 时，在边缘处交集体易出错导致凹槽“埋没、顶面不可见”；
                        # 直接 cut(text_solid) 让凹槽顶面严格等于键帽（弧面）表面，偏到边缘也可见。
                        if is_convex:
                            keycap = keycap.union(curved_part)
                        else:
                            keycap = keycap.cut(curved_part)
                        # 在 cut 前先算“凹槽内填充体”= 文字柱 ∩ 键帽，形状与凹槽一致、不超出键帽，供 3D 显示“文字填充”
                        try:
                            text_trimmed = text_solid.intersect(keycap)
                        except Exception:
                            text_trimmed = None
                        keycap = keycap.cut(text_solid)
                        print("【文字+弧面】凹陷：弧面合并/切割后直接 cut 文字柱体，返回凹槽内填充体供显示")
                    else:
                        # 凸起：1) 先弧面与键帽合并(凸)或切割(凹) 2) 文字与弧面体 intersect 限定在弧面区域（凹陷弧面时键帽已切掉碗，用弧面体裁） 3) union 到键帽
                        if is_convex:
                            keycap = keycap.union(curved_part)
                            text_trimmed = text_solid  # 凸起弧面时文字与弧面 z 几乎不重叠，直接 union
                        else:
                            keycap = keycap.cut(curved_part)
                            text_trimmed = text_solid.intersect(curved_part)  # 凹陷弧面：用碗体裁到碗内
                        keycap = keycap.union(text_trimmed)
                        print("【文字+弧面】凸起：弧面切割后底面贴合弧面，已与键帽合并")
                    return keycap, text_trimmed
                except Exception as e:
                    print(f"【文字+弧面】弧面文字布尔失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return keycap, None
        
        # 无弧面或未传入弧面体：按平面顶面处理
        text_model = self.generate_text_model()
        if text_model is None:
            return keycap, None
        top_z = top_thickness
        text_model = text_model.translate((0, 0, top_z))
        if text_depth > 0:
            try:
                keycap = keycap.cut(text_model)
                print(f"文字已嵌入顶面（凹陷，深度={text_depth:.2f}mm）")
            except Exception as e:
                print(f"从顶面中减去文字时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            try:
                keycap = keycap.union(text_model)
                print(f"文字已生成（凸起，高度={abs(text_depth):.2f}mm）")
            except Exception as e:
                print(f"将文字模型与按键合并时出错: {e}")
                import traceback
                traceback.print_exc()
        return keycap, text_model
    
    def _calculate_arc_height_offset(self) -> float:
        """
        计算弧面高度偏移（文字应该放置的Z位置相对于原始顶面的偏移）
        
        返回:
            正值表示弧面向上凸起的高度（文字需要上移）
            负值表示弧面向下凹陷的深度（文字需要下移）
            0表示没有弧面
        """
        from math import sqrt, tan, radians
        
        # 检查是否启用弧面
        curved_enabled = getattr(self.params.geometry, 'curved_top_enabled', False)
        if not curved_enabled:
            return 0.0
        
        curved_x = getattr(self.params.geometry, 'curved_top_x_enabled', False)
        curved_y = getattr(self.params.geometry, 'curved_top_y_enabled', False)
        
        if not curved_x and not curved_y:
            return 0.0
        
        curved_x_radius = getattr(self.params.geometry, 'curved_top_x_radius', 90.0)
        curved_y_radius = getattr(self.params.geometry, 'curved_top_y_radius', 90.0)
        curved_direction = getattr(self.params.geometry, 'curved_top_direction', 'convex')
        
        is_convex = (curved_direction == "convex")
        
        # 计算顶面实际尺寸（考虑侧面斜角）
        w = self.params.key_width
        h = self.params.key_height
        d = self.params.key_depth
        side_angle = radians(self.params.side_angle)
        
        top_w = w - 2 * d * tan(side_angle) if side_angle > 0 else w
        top_h = h - 2 * d * tan(side_angle) if side_angle > 0 else h
        
        # 计算各方向弧高
        arc_height_x = 0.0
        arc_height_y = 0.0
        
        if curved_x:
            chord_half = top_w / 2
            if 2 * curved_x_radius >= top_w:
                h_val = sqrt(curved_x_radius * curved_x_radius - chord_half * chord_half)
                arc_height_x = curved_x_radius - h_val
        
        if curved_y:
            chord_half = top_h / 2
            if 2 * curved_y_radius >= top_h:
                h_val = sqrt(curved_y_radius * curved_y_radius - chord_half * chord_half)
                arc_height_y = curved_y_radius - h_val
        
        # 计算最终弧高
        if curved_x and curved_y:
            # 双方向弧面（两个圆柱的交集）
            # 交集的最高/最低点是两个弧高中的较小值
            # 因为点必须同时在两个圆柱内
            arc_height = min(arc_height_x, arc_height_y)
            print(f"【弧面高度计算】双方向: arc_height_x={arc_height_x:.2f}mm, arc_height_y={arc_height_y:.2f}mm, 取min={arc_height:.2f}mm")
        elif curved_x:
            arc_height = arc_height_x
            print(f"【弧面高度计算】X方向: arc_height={arc_height:.2f}mm")
        elif curved_y:
            arc_height = arc_height_y
            print(f"【弧面高度计算】Y方向: arc_height={arc_height:.2f}mm")
        else:
            arc_height = 0.0
        
        # 返回弧高（凸起=凸起高度，凹陷=碗深，均为正数，供“弧面切割”用）
        return arc_height
