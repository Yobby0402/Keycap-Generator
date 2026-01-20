"""
按键形状定义和生成
"""
import cadquery as cq
from math import tan, radians
from core.parameters import KeycapParameters


class KeycapShape:
    """按键形状生成器"""
    
    def __init__(self, params: KeycapParameters):
        self.params = params
    
    def generate_keycap_body(self) -> cq.Workplane:
        """
        生成按键本体
        键帽结构：
        - 顶面：与手指接触的面，有厚度，位于Z=0到Z=-top_thickness
        - 四个侧面：从顶面边缘向下延伸，形成壁厚
        - 连接器：在顶面下方，用于连接键轴
        
        返回CadQuery Workplane对象
        """
        w = self.params.key_width
        h = self.params.key_height
        d = self.params.key_depth
        side_angle = radians(self.params.side_angle)
        wall_thickness = self.params.wall_thickness
        top_thickness = self.params.top_thickness
        corner_radius = self.params.corner_radius
        
        # 计算顶面尺寸（考虑侧面斜角）
        # 如果侧面有斜角，顶面会变小
        top_w = w - 2 * d * tan(side_angle) if side_angle > 0 else w
        top_h = h - 2 * d * tan(side_angle) if side_angle > 0 else h
        
        # 1. 创建顶面（带厚度）
        # 顶面在Z=0到Z=top_thickness（顶部在Z=top_thickness，底部在Z=0）
        # 注意：为了正确显示，顶面应该在Z轴正方向
        top_face = (cq.Workplane("XY")
                    .rect(top_w, top_h)
                    .extrude(top_thickness))  # 向上挤出到Z=top_thickness
        
        # 2. 创建四个侧面（从顶面边缘向下延伸）
        # 计算侧面底部尺寸
        bottom_w = w
        bottom_h = h
        side_height = d - top_thickness  # 侧面的高度（从顶面底部到底部）
        
        # 创建侧面（使用loft从顶面边缘到底部边缘）
        # 从Z=top_thickness（顶面顶部）开始，向下延伸到Z=0
        sides = (cq.Workplane("XY")
                 .workplane(offset=top_thickness)  # 从顶面顶部开始
                 .rect(top_w, top_h)
                 .workplane(offset=-side_height)  # 到底部（Z=0）
                 .rect(bottom_w, bottom_h)
                 .loft())
        
        # 合并顶面和侧面
        keycap = top_face.union(sides)
        
        # 3. 创建内部空腔（用于挖空，创建壁厚）
        # 计算内部尺寸
        inner_top_w = max(0.1, top_w - 2 * wall_thickness)
        inner_top_h = max(0.1, top_h - 2 * wall_thickness)
        inner_bottom_w = max(0.1, bottom_w - 2 * wall_thickness)
        inner_bottom_h = max(0.1, bottom_h - 2 * wall_thickness)
        inner_side_height = side_height - wall_thickness
        
        # 创建内部空腔（从顶面内部到底部）
        # 从Z=top_thickness-wall_thickness（顶面内部）开始，向下延伸到Z=0
        inner_cavity = (cq.Workplane("XY")
                        .workplane(offset=top_thickness - wall_thickness)  # 从顶面内部开始
                        .rect(inner_top_w, inner_top_h)
                        .workplane(offset=-(top_thickness - wall_thickness + inner_side_height))  # 到底部
                        .rect(inner_bottom_w, inner_bottom_h)
                        .loft())
        
        # 从键帽中减去内部空腔（创建壁厚，底部仍然开口）
        try:
            keycap = keycap.cut(inner_cavity)
            print("内部空腔已创建（壁厚）")
        except Exception as e:
            print(f"创建内部空腔时出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 4. 添加轴体连接结构（在顶面下方创建连接器空腔）
        if self.params.stem_enabled:
            print("开始添加连接器...")
            keycap = self._add_stem(keycap)
            print("连接器处理完成")
        else:
            print("连接器已禁用")
        
        return keycap
    
    def _add_stem(self, keycap: cq.Workplane) -> cq.Workplane:
        """
        添加轴体连接结构
        """
        if self.params.stem_type == "MX":
            return self._add_mx_stem(keycap)
        elif self.params.stem_type == "Alps":
            return self._add_alps_stem(keycap)
        else:
            return keycap
    
    def _add_mx_stem(self, keycap: cq.Workplane) -> cq.Workplane:
        """
        添加MX轴体连接结构
        连接器位于顶面下方，用于连接键轴
        MX轴体是十字形，键帽需要有一个圆柱形空腔，然后和十字形进行布尔求差
        """
        # MX轴体参数（从参数中获取）
        stem_height = self.params.stem_height
        cross_width = self.params.stem_cross_width
        cross_length = self.params.stem_cross_length
        cylinder_diameter = self.params.stem_cylinder_diameter
        
        # 连接器位置：在顶面下方（Z=0，即顶面底部）向下延伸
        # 注意：由于顶面在Z=0到Z=top_thickness，连接器应该在Z=0处向下延伸
        stem_start_z = 0.0  # 顶面底部（Z=0）
        
        print(f"创建连接器：位置Z={stem_start_z}, 深度={stem_height}mm, 圆柱直径={cylinder_diameter}mm, 十字={cross_length}x{cross_width}mm")
        
        # 创建连接器空腔
        # 方法：创建圆柱形空腔，然后从圆柱中减去十字形
        # 创建圆柱形空腔（从Z=0向下延伸到Z=-stem_height）
        cylinder = (cq.Workplane("XY")
                    .workplane(offset=stem_start_z)  # 从顶面底部（Z=0）开始
                    .circle(cylinder_diameter / 2)
                    .extrude(-stem_height))  # 向下延伸到Z=-stem_height
        
        print(f"圆柱创建完成：从Z={stem_start_z}到Z={stem_start_z - stem_height}")
        
        # 创建十字形（键轴形状）
        # 水平部分（从Z=0向下延伸到Z=-stem_height）
        cross_h = (cq.Workplane("XY")
                   .workplane(offset=stem_start_z)  # Z=0
                   .center(0, 0)
                   .rect(cross_length, cross_width)
                   .extrude(-stem_height))  # 向下延伸到Z=-stem_height
        
        # 垂直部分（从Z=0向下延伸到Z=-stem_height）
        cross_v = (cq.Workplane("XY")
                   .workplane(offset=stem_start_z)  # Z=0
                   .center(0, 0)
                   .rect(cross_width, cross_length)
                   .extrude(-stem_height))  # 向下延伸到Z=-stem_height
        
        print(f"十字形创建完成：从Z={stem_start_z}到Z={stem_start_z - stem_height}")
        
        # 合并十字形
        # 使用更可靠的方法：先创建一个，然后添加另一个
        try:
            # 方法1：直接union
            cross = cross_h.union(cross_v)
            print("十字形union成功")
        except Exception as e:
            print(f"合并十字形时出错，尝试替代方法: {e}")
            # 方法2：使用组合方式创建十字
            try:
                # 创建一个完整的十字形状
                # 先创建水平矩形
                cross = (cq.Workplane("XY")
                         .workplane(offset=stem_start_z)
                         .center(0, 0)
                         .rect(cross_length, cross_width)
                         .extrude(-stem_height))
                
                # 然后添加垂直矩形（使用组合）
                cross_v_new = (cq.Workplane("XY")
                              .workplane(offset=stem_start_z)
                              .center(0, 0)
                              .rect(cross_width, cross_length)
                              .extrude(-stem_height))
                
                # 尝试合并
                cross = cross.union(cross_v_new)
                print("十字形替代方法成功")
            except Exception as e2:
                print(f"替代方法也失败: {e2}")
                # 如果还是失败，尝试简化：只创建圆柱空腔（不带十字）
                print("警告：无法创建十字形，将只使用圆柱空腔")
                cross = None
        
        # 从圆柱中减去十字，得到键帽连接器空腔形状
        # 这个空腔是：圆柱 - 十字 = 可以容纳键轴的形状
        if cross is not None:
            try:
                stem_cavity = cylinder.cut(cross)
                print("连接器空腔创建成功（圆柱-十字）")
            except Exception as e:
                print(f"创建连接器空腔时出错: {e}")
                import traceback
                traceback.print_exc()
                # 如果失败，尝试只使用圆柱（至少能看到连接器位置）
                print("尝试只使用圆柱作为连接器空腔")
                stem_cavity = cylinder
        else:
            # 如果十字创建失败，只使用圆柱
            print("使用圆柱作为连接器空腔（无十字）")
            stem_cavity = cylinder
        
        # 从键帽中减去连接器空腔
        # 注意：连接器空腔在Z=0到Z=-stem_height，应该与键帽的底部（Z=0）连接
        try:
            # 检查键帽是否有实体
            # 使用union将连接器添加到键帽内部
            keycap = keycap.union(stem_cavity)
            print(f"连接器已添加到键帽（位置Z={stem_start_z}到Z={stem_start_z - stem_height}）")
        except Exception as e:
            print(f"从键帽中减去连接器空腔时出错: {e}")
            print("可能的原因：键帽结构问题或连接器位置不正确")
            import traceback
            traceback.print_exc()
            # 尝试调试：检查键帽和连接器的位置
            print(f"键帽范围检查：连接器在Z={stem_start_z}到Z={stem_start_z - stem_height}")
        
        return keycap
    
    def _add_alps_stem(self, keycap: cq.Workplane) -> cq.Workplane:
        """
        添加Alps轴体连接结构
        Alps轴体是矩形，键帽需要有一个矩形空腔
        """
        # Alps轴体参数
        stem_width = 2.0  # mm
        stem_length = 4.0  # mm
        stem_height = self.params.stem_height  # 使用参数中的深度
        
        # 连接器位置：在顶面下方（Z=0，即顶面底部）向下延伸
        stem_start_z = 0.0  # 顶面底部（Z=0）
        
        print(f"创建Alps连接器：位置Z={stem_start_z}, 深度={stem_height}mm, 尺寸={stem_width}x{stem_length}mm")
        
        # 创建支撑圆柱（与MX相同，但中间是矩形孔）
        cylinder_diameter = self.params.stem_cylinder_diameter
        
        # 创建圆柱形外壳
        cylinder = (cq.Workplane("XY")
                    .workplane(offset=stem_start_z)
                    .circle(cylinder_diameter / 2)
                    .extrude(-stem_height))

        # 创建矩形空腔
        stem_hole = (cq.Workplane("XY")
                      .workplane(offset=stem_start_z)
                      .rect(stem_width, stem_length)
                      .extrude(-stem_height))
        
        # 创建带孔的连接器
        try:
            stem = cylinder.cut(stem_hole)
            # 添加到键帽
            keycap = keycap.union(stem)
            print("Alps连接器已添加到键帽")
        except Exception as e:
            print(f"从键帽中减去Alps连接器空腔时出错: {e}")
            import traceback
            traceback.print_exc()
        
        return keycap
