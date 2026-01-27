"""
按键形状定义和生成
"""
import cadquery as cq
from math import tan, radians, sqrt, acos, sin, cos, pi
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
        try:
            # 验证生成的形状是否有效
            if top_face is None:
                print("错误：顶面生成失败")
                return None
            
            # 检查顶面是否有有效的形状
            try:
                top_face_val = top_face.val()
                if top_face_val is None:
                    print("错误：顶面形状为None")
                    return None
                
                # 检查顶面的边界框（这会验证形状是否有效）
                top_bbox = top_face_val.BoundingBox()
                print(f"【顶面】边界框: X:[{top_bbox.xmin:.2f}, {top_bbox.xmax:.2f}], Y:[{top_bbox.ymin:.2f}, {top_bbox.ymax:.2f}], Z:[{top_bbox.zmin:.2f}, {top_bbox.zmax:.2f}]")
                
            except Exception as e:
                print(f"错误：无法验证顶面形状: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            # 检查侧面是否有有效的形状
            try:
                sides_val = sides.val()
                if sides_val is None:
                    print("错误：侧面形状为None")
                    return None
                
                # 检查侧面的边界框
                sides_bbox = sides_val.BoundingBox()
                print(f"【侧面】边界框: X:[{sides_bbox.xmin:.2f}, {sides_bbox.xmax:.2f}], Y:[{sides_bbox.ymin:.2f}, {sides_bbox.ymax:.2f}], Z:[{sides_bbox.zmin:.2f}, {sides_bbox.zmax:.2f}]")
                
                # 检查顶面和侧面是否在Z=top_thickness处接触
                if abs(top_bbox.zmax - sides_bbox.zmax) > 0.1:
                    print(f"警告：顶面和侧面的顶部Z位置不匹配！顶面顶部Z={top_bbox.zmax:.2f}，侧面顶部Z={sides_bbox.zmax:.2f}")
                
            except Exception as e:
                print(f"错误：无法验证侧面形状: {e}")
                import traceback
                traceback.print_exc()
                return None
            
            # 执行union操作
            print(f"【合并】开始合并顶面和侧面...")
            print(f"【合并】顶面Z范围: [{top_bbox.zmin:.2f}, {top_bbox.zmax:.2f}]")
            print(f"【合并】侧面Z范围: [{sides_bbox.zmin:.2f}, {sides_bbox.zmax:.2f}]")
            print(f"【合并】期望：顶面顶部Z={top_thickness:.2f}，侧面顶部Z={top_thickness:.2f}")
            
            # 检查是否有重叠
            z_overlap = min(top_bbox.zmax, sides_bbox.zmax) - max(top_bbox.zmin, sides_bbox.zmin)
            if z_overlap < 0:
                print(f"【合并】警告：顶面和侧面在Z方向没有重叠！重叠={z_overlap:.2f}mm")
                print(f"【合并】尝试调整侧面位置...")
                # 可能需要调整侧面的位置，但先尝试union看看
            
            keycap = top_face.union(sides)
            print(f"【合并】合并成功")
            
            # 验证union后的形状
            try:
                keycap_val = keycap.val()
                if keycap_val is None:
                    print("错误：union后的形状为None")
                    # 尝试只返回顶面
                    return top_face
                
                # 检查union后的边界框
                keycap_bbox = keycap_val.BoundingBox()
                print(f"【合并后】边界框: X:[{keycap_bbox.xmin:.2f}, {keycap_bbox.xmax:.2f}], Y:[{keycap_bbox.ymin:.2f}, {keycap_bbox.ymax:.2f}], Z:[{keycap_bbox.zmin:.2f}, {keycap_bbox.zmax:.2f}]")
                
            except Exception as e:
                print(f"警告：无法验证union后的形状: {e}，继续处理")
                
        except Exception as e:
            print(f"错误：合并顶面和侧面时出错: {e}")
            import traceback
            traceback.print_exc()
            # 如果union失败，尝试只返回顶面
            print("警告：union失败，只返回顶面")
            return top_face
        
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
        
        # 6. 添加弧面（若 skip_curved 则由调用方在弧面体上做文字布尔后再合并）
        self._top_w, self._top_h, self._top_thickness = top_w, top_h, top_thickness
        skip_curved = getattr(self, '_skip_curved_this_build', False)
        if not skip_curved:
            keycap = self._apply_curved_top(keycap, top_w, top_h, top_thickness)
        
        return keycap
    
    def build_curved_surface_only(self, top_w: float = None, top_h: float = None, top_thickness: float = None):
        """
        仅生成弧面体，不合并到键帽。用于“先对弧面做文字布尔，再与键帽合并”，使文字顶面/底面完全贴合弧面。
        返回 (curved_part, is_convex)。无弧面时为 (None, False)。
        """
        tw = top_w if top_w is not None else getattr(self, '_top_w', None)
        th = top_h if top_h is not None else getattr(self, '_top_h', None)
        tt = top_thickness if top_thickness is not None else getattr(self, '_top_thickness', None)
        if tw is None or th is None or tt is None:
            from math import tan, radians
            w, h, d = self.params.key_width, self.params.key_height, self.params.key_depth
            sa = radians(self.params.side_angle)
            tw = w - 2 * d * tan(sa) if sa > 0 else w
            th = h - 2 * d * tan(sa) if sa > 0 else h
            tt = self.params.top_thickness
        
        enabled = getattr(self.params.geometry, 'curved_top_enabled', False)
        cx = getattr(self.params.geometry, 'curved_top_x_enabled', False)
        cy = getattr(self.params.geometry, 'curved_top_y_enabled', False)
        rx = getattr(self.params.geometry, 'curved_top_x_radius', 90.0)
        ry = getattr(self.params.geometry, 'curved_top_y_radius', 90.0)
        is_convex = getattr(self.params.geometry, 'curved_top_direction', 'convex') == 'convex'
        
        if not enabled or (not cx and not cy):
            return None, False
        if cx and 2 * rx < tw:
            return None, False
        if cy and 2 * ry < th:
            return None, False
        
        try:
            if cx and cy:
                chx, chy = tw / 2, th / 2
                hx = sqrt(rx * rx - chx * chx)
                hy = sqrt(ry * ry - chy * chy)
                ax, ay = rx - hx, ry - hy
                total_h = ax + ay
                if is_convex:
                    cx_z, cy_z = tt - hx, tt - hy
                    cyl_x = (cq.Workplane("XZ").workplane(offset=0).center(0, cx_z).circle(rx).extrude(th * 2, both=True))
                    cyl_y = (cq.Workplane("YZ").workplane(offset=0).center(0, cy_z).circle(ry).extrude(tw * 2, both=True))
                    body = cyl_x.intersect(cyl_y)
                    box = (cq.Workplane("XY").workplane(offset=tt).rect(tw, th).extrude(total_h + 0.5))
                else:
                    cx_z, cy_z = tt + hx, tt + hy
                    ext = max(tw, th) * 2
                    cyl_x = (cq.Workplane("XZ").workplane(offset=0).center(0, cx_z).circle(rx).extrude(ext, both=True))
                    cyl_y = (cq.Workplane("YZ").workplane(offset=0).center(0, cy_z).circle(ry).extrude(ext, both=True))
                    body = cyl_x.intersect(cyl_y)
                    box = (cq.Workplane("XY").workplane(offset=tt - total_h - 0.5).rect(ext, ext).extrude(total_h + 0.5))
                part = body.intersect(box)
            elif cx:
                ch = tw / 2
                h = sqrt(rx * rx - ch * ch)
                ah = rx - h
                cz = tt - h if is_convex else tt + h
                ext = max(th, tw) * 2 if not is_convex else th
                cyl = (cq.Workplane("XZ").workplane(offset=0).center(0, cz).circle(rx).extrude(ext, both=True))
                if is_convex:
                    box = (cq.Workplane("XY").workplane(offset=tt).rect(tw, th).extrude(ah + 0.1))
                else:
                    box = (cq.Workplane("XY").workplane(offset=tt - ah - 0.1).rect(tw, ext).extrude(ah + 0.2))
                part = cyl.intersect(box)
            else:
                ch = th / 2
                h = sqrt(ry * ry - ch * ch)
                ah = ry - h
                cz = tt - h if is_convex else tt + h
                ext = max(tw, th) * 2 if not is_convex else tw
                cyl = (cq.Workplane("YZ").workplane(offset=0).center(0, cz).circle(ry).extrude(ext, both=True))
                if is_convex:
                    box = (cq.Workplane("XY").workplane(offset=tt).rect(tw, th).extrude(ah + 0.1))
                else:
                    box = (cq.Workplane("XY").workplane(offset=tt - ah - 0.1).rect(ext, th).extrude(ah + 0.2))
                part = cyl.intersect(box)
            
            return part, is_convex
        except Exception as e:
            print(f"【弧面体】build_curved_surface_only 失败: {e}")
            import traceback
            traceback.print_exc()
            return None, False
    
    def _create_top_surface(self, top_w: float, top_h: float, top_thickness: float) -> cq.Workplane:
        """
        创建平面顶面
        
        参数:
            top_w: 顶面宽度 (mm) - 已考虑侧面斜角
            top_h: 顶面高度 (mm) - 已考虑侧面斜角
            top_thickness: 顶面厚度 (mm)
        
        返回:
            CadQuery Workplane对象
        
        注意：顶面从Z=0向上挤出到Z=top_thickness
        弧面处理在 _apply_curved_top 中进行（在键帽完成后）
        """
        # 始终创建平面顶面，弧面处理在后续步骤中进行
        top_face = (cq.Workplane("XY")
                   .rect(top_w, top_h)
                   .extrude(top_thickness))
        return top_face
    
    def _apply_curved_top(self, keycap: cq.Workplane, top_w: float, top_h: float, top_thickness: float) -> cq.Workplane:
        """
        在完成的键帽上应用弧面
        
        通过布尔运算在顶面上添加（凸起）或删除（凹陷）弧面体
        
        参数:
            keycap: 完成的键帽模型
            top_w: 顶面宽度 (mm)
            top_h: 顶面高度 (mm)
            top_thickness: 顶面厚度 (mm)
        """
        # 检查是否启用弧面
        curved_enabled = getattr(self.params.geometry, 'curved_top_enabled', False)
        curved_x = getattr(self.params.geometry, 'curved_top_x_enabled', False)
        curved_y = getattr(self.params.geometry, 'curved_top_y_enabled', False)
        curved_x_radius = getattr(self.params.geometry, 'curved_top_x_radius', 90.0)
        curved_y_radius = getattr(self.params.geometry, 'curved_top_y_radius', 90.0)
        curved_direction = getattr(self.params.geometry, 'curved_top_direction', 'convex')
        
        print(f"【弧面处理】curved_enabled={curved_enabled}, curved_x={curved_x}, curved_y={curved_y}")
        
        if not curved_enabled or (not curved_x and not curved_y):
            print("【弧面处理】未启用弧面，跳过")
            return keycap
        
        is_convex = (curved_direction == "convex")
        print(f"【弧面处理】方向: {'凸起' if is_convex else '凹陷'}")
        
        # 验证圆弧直径是否满足要求
        if curved_x and 2 * curved_x_radius < top_w:
            print(f"【弧面处理】警告：X方向圆弧直径({2*curved_x_radius:.2f}mm) < 顶面宽度({top_w:.2f}mm)，跳过弧面")
            return keycap
        if curved_y and 2 * curved_y_radius < top_h:
            print(f"【弧面处理】警告：Y方向圆弧直径({2*curved_y_radius:.2f}mm) < 顶面高度({top_h:.2f}mm)，跳过弧面")
            return keycap
        
        try:
            if curved_x and curved_y:
                # 双方向弧面
                keycap = self._apply_double_curved(keycap, top_w, top_h, top_thickness,
                                                   curved_x_radius, curved_y_radius, is_convex)
            elif curved_x:
                # X方向弧面
                keycap = self._apply_x_curved(keycap, top_w, top_h, top_thickness,
                                             curved_x_radius, is_convex)
            elif curved_y:
                # Y方向弧面
                keycap = self._apply_y_curved(keycap, top_w, top_h, top_thickness,
                                             curved_y_radius, is_convex)
            
            print("【弧面处理】完成")
        except Exception as e:
            print(f"【弧面处理】失败: {e}")
            import traceback
            traceback.print_exc()
        
        return keycap
    
    def _apply_x_curved(self, keycap: cq.Workplane, top_w: float, top_h: float, 
                        top_thickness: float, radius: float, is_convex: bool) -> cq.Workplane:
        """
        应用X方向弧面
        创建一个圆柱形弧面体，然后通过布尔运算添加或删除
        """
        try:
            # 计算弧面参数
            chord_half = top_w / 2  # 弦长的一半
            h = sqrt(radius * radius - chord_half * chord_half)  # 弦到圆心的距离
            
            # 弧高 = 圆心到弧的最高点距离 - 弦到圆心的距离
            arc_height = radius - h
            
            print(f"【X方向弧面】半径={radius:.2f}mm, 弦长={top_w:.2f}mm, 弧高={arc_height:.2f}mm")
            
            # 创建圆柱体（在XZ平面，沿Y方向拉伸）
            # 圆柱中心位置：
            # - 对于凸起：圆心在Z = top_thickness - h（圆弧向上凸起）
            # - 对于凹陷：圆心在Z = top_thickness + h（圆弧向下凹陷）
            
            if is_convex:
                # 凸起：创建圆柱体，然后与键帽取交集（只保留顶面范围内的部分）
                # 圆柱中心在 Z = top_thickness - h
                cylinder_center_z = top_thickness - h
                
                # 创建圆柱体（沿Y轴方向）
                cylinder = (cq.Workplane("XZ")
                           .workplane(offset=0)  # Y=0
                           .center(0, cylinder_center_z)  # 圆心在(X=0, Z=cylinder_center_z)
                           .circle(radius)
                           .extrude(top_h, both=True))  # 沿Y方向拉伸
                
                # 创建裁剪盒：只保留顶面范围内的部分
                # 范围：X从-top_w/2到top_w/2，Y从-top_h/2到top_h/2，Z从top_thickness到top_thickness+arc_height
                clip_box = (cq.Workplane("XY")
                           .workplane(offset=top_thickness)
                           .rect(top_w, top_h)
                           .extrude(arc_height + 0.1))
                
                # 取圆柱与裁剪盒的交集
                curved_part = cylinder.intersect(clip_box)
                
                # 将弧面部分添加到键帽上
                keycap = keycap.union(curved_part)
                print(f"【X方向弧面】凸起弧面已添加")
                
            else:
                # 凹陷：创建圆柱体，然后从键帽中减去
                # 圆柱中心在 Z = top_thickness + h
                cylinder_center_z = top_thickness + h
                
                # 创建圆柱体（沿Y轴方向）
                # 拉伸长度需要足够大以穿透侧面
                extrude_length = max(top_h, top_w) * 2
                cylinder = (cq.Workplane("XZ")
                           .workplane(offset=0)
                           .center(0, cylinder_center_z)
                           .circle(radius)
                           .extrude(extrude_length, both=True))
                
                # 创建裁剪盒：X方向限制在顶面宽度内，Y方向足够大以穿透侧面
                clip_box = (cq.Workplane("XY")
                           .workplane(offset=top_thickness - arc_height - 0.1)
                           .rect(top_w, extrude_length)
                           .extrude(arc_height + 0.2))
                
                # 取圆柱与裁剪盒的交集
                curved_part = cylinder.intersect(clip_box)
                
                # 从键帽中减去弧面部分
                keycap = keycap.cut(curved_part)
                print(f"【X方向弧面】凹陷弧面已减去")
            
            return keycap
            
        except Exception as e:
            print(f"【X方向弧面】失败: {e}")
            import traceback
            traceback.print_exc()
            return keycap
    
    def _apply_y_curved(self, keycap: cq.Workplane, top_w: float, top_h: float, 
                        top_thickness: float, radius: float, is_convex: bool) -> cq.Workplane:
        """
        应用Y方向弧面
        创建一个圆柱形弧面体，然后通过布尔运算添加或删除
        """
        try:
            # 计算弧面参数
            chord_half = top_h / 2  # 弦长的一半
            h = sqrt(radius * radius - chord_half * chord_half)  # 弦到圆心的距离
            
            # 弧高 = 圆心到弧的最高点距离 - 弦到圆心的距离
            arc_height = radius - h
            
            print(f"【Y方向弧面】半径={radius:.2f}mm, 弦长={top_h:.2f}mm, 弧高={arc_height:.2f}mm")
            
            if is_convex:
                # 凸起：圆柱中心在 Z = top_thickness - h
                cylinder_center_z = top_thickness - h
                
                # 创建圆柱体（沿X轴方向）
                cylinder = (cq.Workplane("YZ")
                           .workplane(offset=0)  # X=0
                           .center(0, cylinder_center_z)  # 圆心在(Y=0, Z=cylinder_center_z)
                           .circle(radius)
                           .extrude(top_w, both=True))  # 沿X方向拉伸
                
                # 创建裁剪盒
                clip_box = (cq.Workplane("XY")
                           .workplane(offset=top_thickness)
                           .rect(top_w, top_h)
                           .extrude(arc_height + 0.1))
                
                # 取交集并添加到键帽
                curved_part = cylinder.intersect(clip_box)
                keycap = keycap.union(curved_part)
                print(f"【Y方向弧面】凸起弧面已添加")
                
            else:
                # 凹陷：圆柱中心在 Z = top_thickness + h
                cylinder_center_z = top_thickness + h
                
                # 拉伸长度需要足够大以穿透侧面
                extrude_length = max(top_w, top_h) * 2
                cylinder = (cq.Workplane("YZ")
                           .workplane(offset=0)
                           .center(0, cylinder_center_z)
                           .circle(radius)
                           .extrude(extrude_length, both=True))
                
                # 创建裁剪盒：Y方向限制在顶面高度内，X方向足够大以穿透侧面
                clip_box = (cq.Workplane("XY")
                           .workplane(offset=top_thickness - arc_height - 0.1)
                           .rect(extrude_length, top_h)
                           .extrude(arc_height + 0.2))
                
                curved_part = cylinder.intersect(clip_box)
                keycap = keycap.cut(curved_part)
                print(f"【Y方向弧面】凹陷弧面已减去")
            
            return keycap
            
        except Exception as e:
            print(f"【Y方向弧面】失败: {e}")
            import traceback
            traceback.print_exc()
            return keycap
    
    def _apply_double_curved(self, keycap: cq.Workplane, top_w: float, top_h: float, 
                             top_thickness: float, x_radius: float, y_radius: float, 
                             is_convex: bool) -> cq.Workplane:
        """
        应用双方向弧面（使用两个圆柱面的交集实现平滑过渡）
        
        这种方法生成的曲面在X方向是圆弧，在Y方向也是圆弧，
        且能完整覆盖整个矩形顶面，过渡平滑无交叉痕迹
        """
        try:
            print(f"【双方向弧面】开始处理...")
            print(f"【双方向弧面】顶面尺寸={top_w:.2f}x{top_h:.2f}mm")
            print(f"【双方向弧面】X半径={x_radius:.2f}mm, Y半径={y_radius:.2f}mm")
            
            # 计算X方向弧面参数
            chord_x_half = top_w / 2
            h_x = sqrt(x_radius * x_radius - chord_x_half * chord_x_half)
            arc_height_x = x_radius - h_x
            
            # 计算Y方向弧面参数
            chord_y_half = top_h / 2
            h_y = sqrt(y_radius * y_radius - chord_y_half * chord_y_half)
            arc_height_y = y_radius - h_y
            
            # 总弧高（两个方向弧高的和）
            total_arc_height = arc_height_x + arc_height_y
            
            print(f"【双方向弧面】弧高X={arc_height_x:.2f}mm, 弧高Y={arc_height_y:.2f}mm, 总弧高={total_arc_height:.2f}mm")
            
            if is_convex:
                # 凸起模式：使用两个圆柱的交集
                # X方向圆柱：圆心在 Z = top_thickness - h_x，轴沿Y方向
                cylinder_x_center_z = top_thickness - h_x
                # Y方向圆柱：圆心在 Z = top_thickness - h_y，轴沿X方向
                cylinder_y_center_z = top_thickness - h_y
                
                # 创建X方向圆柱（沿Y轴方向）
                cylinder_x = (cq.Workplane("XZ")
                             .workplane(offset=0)
                             .center(0, cylinder_x_center_z)
                             .circle(x_radius)
                             .extrude(top_h * 2, both=True))
                
                # 创建Y方向圆柱（沿X轴方向）
                cylinder_y = (cq.Workplane("YZ")
                             .workplane(offset=0)
                             .center(0, cylinder_y_center_z)
                             .circle(y_radius)
                             .extrude(top_w * 2, both=True))
                
                # 取两个圆柱的交集 - 这会产生一个双曲面形状
                curved_body = cylinder_x.intersect(cylinder_y)
                
                # 创建裁剪盒：只保留顶面范围内、Z > top_thickness 的部分
                clip_box = (cq.Workplane("XY")
                           .workplane(offset=top_thickness)
                           .rect(top_w, top_h)
                           .extrude(total_arc_height + 0.5))
                
                # 取弧面体与裁剪盒的交集
                curved_part = curved_body.intersect(clip_box)
                
                # 将弧面部分添加到键帽上
                keycap = keycap.union(curved_part)
                print(f"【双方向弧面】凸起双曲面已添加")
                
            else:
                # 凹陷模式：使用两个圆柱的并集来切割
                # X方向圆柱：圆心在 Z = top_thickness + h_x
                cylinder_x_center_z = top_thickness + h_x
                # Y方向圆柱：圆心在 Z = top_thickness + h_y
                cylinder_y_center_z = top_thickness + h_y
                
                # 拉伸长度足够大以穿透侧面
                extrude_length = max(top_w, top_h) * 2
                
                # 创建X方向圆柱
                cylinder_x = (cq.Workplane("XZ")
                             .workplane(offset=0)
                             .center(0, cylinder_x_center_z)
                             .circle(x_radius)
                             .extrude(extrude_length, both=True))
                
                # 创建Y方向圆柱
                cylinder_y = (cq.Workplane("YZ")
                             .workplane(offset=0)
                             .center(0, cylinder_y_center_z)
                             .circle(y_radius)
                             .extrude(extrude_length, both=True))
                
                # 取两个圆柱的交集 - 凹陷部分
                curved_body = cylinder_x.intersect(cylinder_y)
                
                # 创建裁剪盒：足够大以穿透侧面
                clip_box = (cq.Workplane("XY")
                           .workplane(offset=top_thickness - total_arc_height - 0.5)
                           .rect(extrude_length, extrude_length)
                           .extrude(total_arc_height + 0.5))
                
                # 取弧面体与裁剪盒的交集
                curved_part = curved_body.intersect(clip_box)
                
                # 从键帽中减去弧面部分
                keycap = keycap.cut(curved_part)
                print(f"【双方向弧面】凹陷双曲面已减去")
            
            return keycap
            
        except Exception as e:
            print(f"【双方向弧面】双曲面方法失败: {e}")
            import traceback
            traceback.print_exc()
            # 如果双曲面方法失败，回退到叠加方法
            print(f"【双方向弧面】回退到叠加方法...")
            keycap = self._apply_x_curved(keycap, top_w, top_h, top_thickness, x_radius, is_convex)
            keycap = self._apply_y_curved(keycap, top_w, top_h, top_thickness, y_radius, is_convex)
            return keycap
    
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
