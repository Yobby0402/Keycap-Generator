"""
按键形状定义和生成
"""
import cadquery as cq
from math import tan, radians, sqrt
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
        
        # 1. 创建顶面（根据顶面类型）
        top_face = self._create_top_surface(top_w, top_h, top_thickness)
        
        # 2. 创建四个侧面（从顶面边缘向下延伸）
        # 计算侧面底部尺寸
        bottom_w = w
        bottom_h = h
        # 以总高度d作为侧面下延长度，确保整体高度正确
        side_height = d  # 侧面的高度（从顶面顶部到底部）
        
        # 创建侧面（使用loft从顶面边缘到底部边缘）
        # 从Z=top_thickness（顶面顶部）开始，向下延伸到Z=top_thickness - d
        sides = (cq.Workplane("XY")
                 .workplane(offset=top_thickness)  # 从顶面顶部开始
                 .rect(top_w, top_h)
                 .workplane(offset=-side_height)  # 到底部（Z=top_thickness - d）
                 .rect(bottom_w, bottom_h)
                 .loft())
        
        # 合并顶面和侧面
        keycap = top_face.union(sides)
        
        # 3. 创建内部空腔（用于挖空，创建壁厚）
        # 计算内部尺寸（确保内部尺寸合理，不会导致空腔创建失败）
        # 限制壁厚不能超过按键尺寸的一半，但允许更小的壁厚值
        max_wall_thickness = min(top_w, top_h, bottom_w, bottom_h) / 2 - 0.1
        # 使用实际的wall_thickness，不要过度限制（只要不超过最大值即可）
        effective_wall_thickness = wall_thickness if wall_thickness <= max_wall_thickness else max_wall_thickness
        
        print(f"【内部空腔】开始创建，wall_thickness={wall_thickness:.2f}mm，effective_wall_thickness={effective_wall_thickness:.2f}mm，top_thickness={top_thickness:.2f}mm，d={d:.2f}mm")
        
        if effective_wall_thickness > 0.01:  # 允许很小的壁厚值
            inner_top_w = max(0.1, top_w - 2 * effective_wall_thickness)
            inner_top_h = max(0.1, top_h - 2 * effective_wall_thickness)
            inner_bottom_w = max(0.1, bottom_w - 2 * effective_wall_thickness)
            inner_bottom_h = max(0.1, bottom_h - 2 * effective_wall_thickness)
            
            print(f"【内部空腔】内部尺寸：top({inner_top_w:.2f}x{inner_top_h:.2f})，bottom({inner_bottom_w:.2f}x{inner_bottom_h:.2f})")
            
            # 确保内部空腔不会太大（至少保留一些壁厚）
            if inner_top_w > 0.1 and inner_top_h > 0.1 and inner_bottom_w > 0.1 and inner_bottom_h > 0.1:
                # 创建内部空腔（从顶面内部到底部）
                # 坐标系统说明：
                # - 顶面：从Z=0向上挤出到Z=top_thickness（顶面顶部在Z=top_thickness）
                # - 侧面：从Z=top_thickness向下延伸到Z=top_thickness - d
                # - 整个键帽从Z=top_thickness - d（底部）到Z=top_thickness（顶部）
                # - 内部空腔保留顶部壁厚，底部保持开口
                keycap_bottom_z = top_thickness - d
                top_z = top_thickness - effective_wall_thickness
                # 让空腔略微穿透底部，避免布尔保留封底
                bottom_z = keycap_bottom_z - 0.2
                cavity_height = top_z - bottom_z
                
                print(f"【内部空腔】Z位置：top_z={top_z:.2f}mm，bottom_z={bottom_z:.2f}mm，高度={cavity_height:.2f}mm")
                print(f"【内部空腔】键帽参数：top_thickness={top_thickness:.2f}mm，d={d:.2f}mm，side_height={side_height:.2f}mm，bottom_z={keycap_bottom_z:.2f}mm（底部开口+穿透）")
                
                # 确保空腔高度合理（必须大于0.1mm）
                # 如果空腔高度太小或为负，说明壁厚太大
                if cavity_height <= 0.1:
                    print(f"【内部空腔】✗ 空腔高度太小或为负（{cavity_height:.2f}mm）")
                    print(f"【内部空腔】提示：壁厚不能超过d的一半（当前d={d:.2f}mm，最大壁厚={d/2:.2f}mm）")
                    print(f"【内部空腔】当前壁厚={effective_wall_thickness:.2f}mm，需要 < {d/2:.2f}mm")
                
                if cavity_height > 0.1:
                    # 创建内部空腔（从顶面内部到底部）
                    try:
                        # 使用loft创建空腔：从底部矩形到顶部矩形
                        # 注意：loft从Z=bottom_z放样到Z=top_z
                        inner_cavity = (cq.Workplane("XY")
                                        .workplane(offset=bottom_z)  # 从底部开始（Z=effective_wall_thickness）
                                        .rect(inner_bottom_w, inner_bottom_h)  # 底部矩形
                                        .workplane(offset=cavity_height)  # 向上移动到顶部
                                        .rect(inner_top_w, inner_top_h)  # 顶部矩形
                                        .loft())  # 放样连接两个矩形
                        
                        print(f"【内部空腔】空腔模型已创建，准备切割...")
                        print(f"【内部空腔】空腔尺寸：底部({inner_bottom_w:.2f}x{inner_bottom_h:.2f})@Z={bottom_z:.2f}，顶部({inner_top_w:.2f}x{inner_top_h:.2f})@Z={top_z:.2f}，高度={cavity_height:.2f}mm")
                        
                        # 从键帽中减去内部空腔（创建壁厚，底部仍然开口）
                        keycap = keycap.cut(inner_cavity)
                        print(f"【内部空腔】✓ 成功创建并切割（壁厚={effective_wall_thickness:.2f}mm，顶部Z={top_z:.2f}，底部Z={bottom_z:.2f}，高度={cavity_height:.2f}mm）")
                    except Exception as e:
                        print(f"【内部空腔】✗ 创建失败: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"【内部空腔】✗ 警告：空腔高度太小（{cavity_height:.2f}mm），无法创建（壁厚={effective_wall_thickness:.2f}mm，d={d:.2f}mm）")
                    print(f"【内部空腔】提示：壁厚不能超过d的一半（当前d={d:.2f}mm，最大壁厚={d/2:.2f}mm）")
            else:
                print(f"【内部空腔】✗ 警告：内部尺寸无效，无法创建内部空腔（壁厚={wall_thickness}mm，最大允许={max_wall_thickness:.2f}mm）")
        else:
            print(f"【内部空腔】✗ 警告：壁厚无效或为0，跳过内部空腔创建（wall_thickness={wall_thickness}mm）")
        
        # 4. 添加轴体连接结构（在顶面下方创建连接器空腔）
        if self.params.stem_enabled:
            print("开始添加连接器...")
            keycap = self._add_stem(keycap)
            print("连接器处理完成")
        else:
            print("连接器已禁用")
        
        # 4. 应用边缘形状（圆角/45度斜角）
        edge_mode = getattr(self.params.geometry, 'edge_profile_mode', 'fillet')
        edge_radius = getattr(self.params.geometry, 'edge_profile_radius', 0.0)
        edge_outer = getattr(self.params.geometry, 'edge_profile_outer', True)
        edge_inner = getattr(self.params.geometry, 'edge_profile_inner', False)
        edge_flags = {
            "left": getattr(self.params.geometry, 'edge_profile_left', True),
            "right": getattr(self.params.geometry, 'edge_profile_right', True),
            "top": getattr(self.params.geometry, 'edge_profile_top', True),
            "bottom": getattr(self.params.geometry, 'edge_profile_bottom', True),
        }

        if edge_radius > 0 and (edge_outer or edge_inner):
            # 外侧边缘（顶面上边缘）
            if edge_outer:
                outer_bounds = {
                    "xmin": -top_w / 2,
                    "xmax": top_w / 2,
                    "ymin": -top_h / 2,
                    "ymax": top_h / 2,
                }
                keycap = self._apply_edge_profile(
                    keycap=keycap,
                    z_target=top_thickness,
                    bounds=outer_bounds,
                    edge_flags=edge_flags,
                    mode=edge_mode,
                    radius=edge_radius,
                    label="外侧"
                )

            # 内侧边缘（空腔上边缘）
            if edge_inner and effective_wall_thickness > 0:
                inner_top_z = top_thickness - effective_wall_thickness
                inner_bounds = {
                    "xmin": -inner_top_w / 2,
                    "xmax": inner_top_w / 2,
                    "ymin": -inner_top_h / 2,
                    "ymax": inner_top_h / 2,
                }
                keycap = self._apply_edge_profile(
                    keycap=keycap,
                    z_target=inner_top_z,
                    bounds=inner_bounds,
                    edge_flags=edge_flags,
                    mode=edge_mode,
                    radius=edge_radius,
                    label="内侧"
                )
        
        # 5. 添加卫星轴连接器（用于长按键）
        print("【卫星轴】开始检查参数...")
        stabilizer_enabled = False
        if hasattr(self.params, 'stabilizer_enabled'):
            stabilizer_enabled = self.params.stabilizer_enabled
            print(f"  - 从params.stabilizer_enabled获取: {stabilizer_enabled}")
        elif hasattr(self.params, 'geometry') and hasattr(self.params.geometry, 'stabilizer_enabled'):
            stabilizer_enabled = self.params.geometry.stabilizer_enabled
            print(f"  - 从params.geometry.stabilizer_enabled获取: {stabilizer_enabled}")
        else:
            print(f"  - 未找到stabilizer_enabled参数")
        
        if stabilizer_enabled:
            print("【卫星轴】开始添加卫星轴连接器...")
            keycap = self._add_stabilizer(keycap)
            print("【卫星轴】卫星轴连接器处理完成")
        else:
            print("【卫星轴】未启用，跳过")
        
        return keycap
    
    def _create_top_surface(self, top_w: float, top_h: float, top_thickness: float) -> cq.Workplane:
        """
        创建顶面（带圆角）
        
        参数:
            top_w: 顶面宽度 (mm)
            top_h: 顶面高度 (mm)
            top_thickness: 顶面厚度 (mm)
        
        返回:
            CadQuery Workplane对象
        
        注意：顶面从Z=0向上挤出到Z=top_thickness
        """
        top_fillet_radius = getattr(self.params.geometry, 'top_fillet_radius', 0.0)
        
        # 创建基础矩形（从Z=0向上挤出到Z=top_thickness）
        top_face = (cq.Workplane("XY")
                   .rect(top_w, top_h)
                   .extrude(top_thickness))
        
        # 注意：顶面圆角将在整个模型创建完成后应用（在内部空腔创建之后）
        # 这样可以确保圆角应用到最终的模型上，而不是被后续操作影响
        return top_face

    def _apply_edge_profile(self, keycap: cq.Workplane, z_target: float, bounds: dict,
                            edge_flags: dict, mode: str, radius: float, label: str) -> cq.Workplane:
        """按指定边缘应用圆角/倒角"""
        try:
            tol = 0.05
            max_radius = min(bounds["xmax"] - bounds["xmin"],
                             bounds["ymax"] - bounds["ymin"]) / 2 - 0.05
            safe_radius = min(radius, max_radius)
            if safe_radius <= 0:
                return keycap

            selected_edges = []
            for edge in keycap.val().Edges():
                c = edge.Center()
                if abs(c.z - z_target) > tol:
                    continue
                if edge_flags.get("left") and abs(c.x - bounds["xmin"]) < tol:
                    selected_edges.append(edge)
                if edge_flags.get("right") and abs(c.x - bounds["xmax"]) < tol:
                    selected_edges.append(edge)
                if edge_flags.get("top") and abs(c.y - bounds["ymax"]) < tol:
                    selected_edges.append(edge)
                if edge_flags.get("bottom") and abs(c.y - bounds["ymin"]) < tol:
                    selected_edges.append(edge)

            if not selected_edges:
                print(f"【边缘形状】{label}未找到可处理边（z={z_target:.2f}）")
                return keycap

            edge_wp = cq.Workplane(obj=keycap.val()).newObject(selected_edges)
            if mode == "chamfer":
                keycap = edge_wp.chamfer(safe_radius)
                print(f"【边缘形状】{label} 45度斜角已应用（半径={safe_radius:.2f}mm）")
            else:
                keycap = edge_wp.fillet(safe_radius)
                print(f"【边缘形状】{label} 圆角已应用（半径={safe_radius:.2f}mm）")
        except Exception as e:
            print(f"【边缘形状】{label} 应用失败: {e}")
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
    
    def _add_stabilizer(self, keycap: cq.Workplane) -> cq.Workplane:
        """
        添加卫星轴连接器（用于长按键，如空格键、Shift等）
        卫星轴连接器通常位于按键的两侧，用于连接卫星轴
        """
        # 检查卫星轴是否启用
        stabilizer_enabled = False
        if hasattr(self.params, 'stabilizer_enabled'):
            stabilizer_enabled = self.params.stabilizer_enabled
        elif hasattr(self.params, 'geometry') and hasattr(self.params.geometry, 'stabilizer_enabled'):
            stabilizer_enabled = self.params.geometry.stabilizer_enabled
        
        print(f"【卫星轴检查】stabilizer_enabled = {stabilizer_enabled}")
        print(f"  - hasattr(params, 'stabilizer_enabled'): {hasattr(self.params, 'stabilizer_enabled')}")
        if hasattr(self.params, 'geometry'):
            print(f"  - hasattr(params.geometry, 'stabilizer_enabled'): {hasattr(self.params.geometry, 'stabilizer_enabled')}")
            if hasattr(self.params.geometry, 'stabilizer_enabled'):
                print(f"  - params.geometry.stabilizer_enabled = {self.params.geometry.stabilizer_enabled}")
        
        if not stabilizer_enabled:
            print("【卫星轴】未启用，跳过")
            return keycap
        
        # 获取卫星轴长度
        stabilizer_length = 50.0
        if hasattr(self.params, 'stabilizer_length'):
            stabilizer_length = self.params.stabilizer_length
        elif hasattr(self.params, 'geometry') and hasattr(self.params.geometry, 'stabilizer_length'):
            stabilizer_length = self.params.geometry.stabilizer_length
        
        print(f"【卫星轴】启用: {stabilizer_enabled}, 长度: {stabilizer_length}mm")
        
        # 先获取按键尺寸参数
        w = self.params.key_width
        h = self.params.key_height
        d = self.params.key_depth
        top_thickness = self.params.top_thickness
        wall_thickness = self.params.wall_thickness
        
        # 卫星轴连接器参数
        # 直径：根据按键宽度调整，但最小3.0mm，最大5.0mm（增大以便可见）
        stabilizer_diameter = max(3.0, min(5.0, w * 0.08))
        # 深度：向上延伸的深度，通常4-6mm（增大以便可见）
        stabilizer_depth = 5.0  # 卫星轴连接器深度 (mm)
        
        print(f"【卫星轴】按键尺寸: {w}x{h}mm, 深度: {d}mm, 顶面厚度: {top_thickness}mm")
        
        # 卫星轴连接器位置：在按键底部两侧，距离边缘一定距离
        # 通常位于按键宽度的1/4和3/4位置
        # 对于长按键（如空格键），连接器应该在按键宽度的约1/4和3/4位置
        offset_from_edge = w * 0.2  # 距离边缘20%的位置
        
        # 左侧卫星轴连接器（X坐标）
        left_x = -w / 2 + offset_from_edge
        # 右侧卫星轴连接器（X坐标）
        right_x = w / 2 - offset_from_edge
        
        # 连接器在Y方向居中
        center_y = 0.0
        
        # 连接器位置：在按键底部（Z=0，即底部开口处）
        # 键帽结构说明（重要！）：
        # - 顶面：Z=0（底部）到Z=top_thickness（顶部）
        # - 侧面：从Z=top_thickness向下延伸到Z=0
        # - 底部：在Z=0处开口
        # 
        # 卫星轴连接器应该和MX stem连接器一样的逻辑：
        # 1. 创建空腔（圆柱形），从Z=0向下延伸到Z=-stabilizer_depth（向下延伸，和MX stem一样）
        # 2. 这个空腔用于容纳卫星轴杆
        # 3. 使用union添加到键帽（和MX stem一样）
        
        # 计算连接器的Z位置（和MX stem一样）
        # 从底部（Z=0）向下延伸，创建空腔
        stabilizer_start_z = 0.0  # 底部（Z=0）
        # 连接器深度：向下延伸的深度（和MX stem一样，向下延伸）
        
        print(f"【卫星轴】连接器位置: 左侧({left_x:.2f}, {center_y:.2f}), 右侧({right_x:.2f}, {center_y:.2f})")
        print(f"【卫星轴】连接器Z范围: {stabilizer_start_z} 到 {stabilizer_start_z - stabilizer_depth}mm（向下延伸，和MX stem一样）")
        print(f"【卫星轴】连接器参数: 直径={stabilizer_diameter:.2f}mm, 深度={stabilizer_depth}mm")
        
        # 卫星轴连接器参数（和MX stem类似）
        # 卫星轴连接器也需要十字形结构，但尺寸可能不同
        # 使用和MX stem相同的十字形参数，或者使用较小的尺寸
        cross_width = self.params.stem_cross_width  # 使用MX stem的十字宽度
        cross_length = min(self.params.stem_cross_length, stabilizer_diameter * 0.6)  # 十字长度，不超过连接器直径的60%
        
        # 创建左侧卫星轴连接器空腔（圆柱形，从底部向下延伸，和MX stem一样）
        # 注意：这是空腔，用于容纳卫星轴杆，和MX stem连接器一样的逻辑
        try:
            # 创建圆柱形空腔（从Z=0向下延伸到Z=-stabilizer_depth）
            left_cylinder = (cq.Workplane("XY")
                            .workplane(offset=stabilizer_start_z)  # 从底部（Z=0）开始
                            .center(left_x, center_y)
                            .circle(stabilizer_diameter / 2)
                            .extrude(-stabilizer_depth))  # 向下延伸到Z=-stabilizer_depth
            
            # 创建十字形（和MX stem一样）
            # 水平部分
            left_cross_h = (cq.Workplane("XY")
                           .workplane(offset=stabilizer_start_z)
                           .center(left_x, center_y)
                           .rect(cross_length, cross_width)
                           .extrude(-stabilizer_depth))
            
            # 垂直部分
            left_cross_v = (cq.Workplane("XY")
                           .workplane(offset=stabilizer_start_z)
                           .center(left_x, center_y)
                           .rect(cross_width, cross_length)
                           .extrude(-stabilizer_depth))
            
            # 合并十字形
            try:
                left_cross = left_cross_h.union(left_cross_v)
            except:
                left_cross = left_cross_h
            
            # 从圆柱中减去十字，得到连接器空腔形状（和MX stem一样）
            try:
                left_stabilizer = left_cylinder.cut(left_cross)
                print(f"【卫星轴】左侧连接器创建成功（带十字）: 位置({left_x:.2f}, {center_y:.2f}), Z={stabilizer_start_z}到{stabilizer_start_z - stabilizer_depth:.2f}")
            except:
                # 如果失败，只使用圆柱
                left_stabilizer = left_cylinder
                print(f"【卫星轴】左侧连接器创建成功（仅圆柱）: 位置({left_x:.2f}, {center_y:.2f}), Z={stabilizer_start_z}到{stabilizer_start_z - stabilizer_depth:.2f}")
                
        except Exception as e:
            print(f"【卫星轴】创建左侧连接器失败: {e}")
            import traceback
            traceback.print_exc()
            return keycap
        
        # 创建右侧卫星轴连接器空腔
        try:
            # 创建圆柱形空腔
            right_cylinder = (cq.Workplane("XY")
                             .workplane(offset=stabilizer_start_z)  # 从底部（Z=0）开始
                             .center(right_x, center_y)
                             .circle(stabilizer_diameter / 2)
                             .extrude(-stabilizer_depth))  # 向下延伸到Z=-stabilizer_depth
            
            # 创建十字形
            # 水平部分
            right_cross_h = (cq.Workplane("XY")
                            .workplane(offset=stabilizer_start_z)
                            .center(right_x, center_y)
                            .rect(cross_length, cross_width)
                            .extrude(-stabilizer_depth))
            
            # 垂直部分
            right_cross_v = (cq.Workplane("XY")
                            .workplane(offset=stabilizer_start_z)
                            .center(right_x, center_y)
                            .rect(cross_width, cross_length)
                            .extrude(-stabilizer_depth))
            
            # 合并十字形
            try:
                right_cross = right_cross_h.union(right_cross_v)
            except:
                right_cross = right_cross_h
            
            # 从圆柱中减去十字，得到连接器空腔形状
            try:
                right_stabilizer = right_cylinder.cut(right_cross)
                print(f"【卫星轴】右侧连接器创建成功（带十字）: 位置({right_x:.2f}, {center_y:.2f}), Z={stabilizer_start_z}到{stabilizer_start_z - stabilizer_depth:.2f}")
            except:
                # 如果失败，只使用圆柱
                right_stabilizer = right_cylinder
                print(f"【卫星轴】右侧连接器创建成功（仅圆柱）: 位置({right_x:.2f}, {center_y:.2f}), Z={stabilizer_start_z}到{stabilizer_start_z - stabilizer_depth:.2f}")
                
        except Exception as e:
            print(f"【卫星轴】创建右侧连接器失败: {e}")
            import traceback
            traceback.print_exc()
            return keycap
        
        # 合并两个连接器空腔，然后添加到键帽（和MX stem一样的逻辑）
        try:
            # 先合并两个连接器空腔
            stabilizer_cavity = left_stabilizer.union(right_stabilizer)
            print(f"【卫星轴】连接器合并成功")
            
            # 将连接器空腔添加到键帽（使用union，和MX stem一样）
            print(f"【卫星轴】准备将连接器添加到键帽...")
            print(f"  - 键帽尺寸: {w}x{h}mm, 深度: {d}mm")
            print(f"  - 连接器位置: X范围[{left_x:.2f}, {right_x:.2f}], Y={center_y:.2f}, Z范围[{stabilizer_start_z}, {stabilizer_start_z - stabilizer_depth:.2f}]")
            
            # 执行union操作，将连接器空腔添加到键帽（和MX stem一样）
            keycap = keycap.union(stabilizer_cavity)
            print("【卫星轴】连接器已成功添加到键帽（空腔，带十字形，用于容纳卫星轴杆，和MX stem一样）")
            
            # 验证：检查键帽是否仍然有效
            try:
                # 尝试获取键帽的边界框来验证
                bbox = keycap.val().BoundingBox()
                print(f"【卫星轴】验证：键帽边界框 - X:[{bbox.xmin:.2f}, {bbox.xmax:.2f}], Y:[{bbox.ymin:.2f}, {bbox.ymax:.2f}], Z:[{bbox.zmin:.2f}, {bbox.zmax:.2f}]")
            except:
                print("【卫星轴】警告：无法获取键帽边界框（可能正常）")
                
        except Exception as e:
            print(f"【卫星轴】将连接器添加到键帽失败: {e}")
            import traceback
            traceback.print_exc()
            # 即使失败也返回keycap，不中断生成流程
        
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
