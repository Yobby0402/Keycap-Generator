"""
字体轮廓处理
使用fontTools提取字体轮廓，转换为shapely几何图形
"""
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from shapely.geometry import Polygon, MultiPolygon
import numpy as np

class ShapelyPen(BasePen):
    """将字体轮廓转换为shapely几何图形的Pen"""
    
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.polygons = []
        self.current_polygon = []
        self.start_point = None
        self.current_point = None
    
    def _moveTo(self, pt):
        if self.current_polygon:
            self._closePath()
        self.current_polygon = [pt]
        self.start_point = pt
        self.current_point = pt
    
    def _lineTo(self, pt):
        self.current_polygon.append(pt)
        self.current_point = pt
    
    def _curveToOne(self, p1, p2, p3):
        """三次贝塞尔曲线 (Cubic Bezier) - 单段"""
        if not self.current_point:
            return
            
        p0 = self.current_point
        
        # 采样
        steps = 10
        for j in range(1, steps + 1):
            t = j / steps
            # Cubic Bezier
            it = 1-t
            a = it*it*it
            b = 3*it*it*t
            c = 3*it*t*t
            d = t*t*t
            
            x = a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0]
            y = a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]
            self.current_polygon.append((x, y))
        
        self.current_point = p3
    
    def qCurveTo(self, *points):
        """二次贝塞尔曲线 (Quadratic Bezier)"""
        if not self.current_point:
            return
            
        # 逻辑：将一系列点转换为一系列二次曲线
        # P0(current) -> P1 -> P2 ...
        # 输入 points 是 [P1, P2, P3, ... Pn]
        # 其中最后一个点 Pn 是 on-curve，其余是 off-curve
        # 如果有两个连续的 off-curve 点 P_i, P_{i+1}，则它们中间有一个隐式 on-curve 点 M = (P_i + P_{i+1}) / 2
        
        # 完整的 TrueType qCurve 处理逻辑
        # 首先，我们需要构建完整的 on-curve / off-curve 序列
        # 但 BasePen 的接口简化了这一点：
        # 它保证调用的 points 列表不仅包含 off-curve，最后一个一定是 on-curve (除非只有 off-curve，那是特殊情况，但 fonttools 通常会在最后提供 on-curve)
        
        # 算法：
        # 遍历 points。
        # current P0.
        # list of points to process: P1, P2, ... Pn
        # 实际上这定义了 N-1 段曲线？如果不含隐式点。
        
        # 为了兼容性，我们采用两两处理策略，处理隐式点。
        
        p0 = self.current_point
        
        # 我们需要迭代处理点
        # 但标准的 FontTools 处理方式是将点序列转换为一系列的三点元组 (p0, p1, p2)
        # 既然我们没有内置转换器，我们手动实现一个简化的
        
        if not points: return
        
        # 处理逻辑
        i = 0
        while i < len(points) - 1:
            p1 = points[i]
            p2 = points[i+1]
            
            # 如果这只是这一段的结束
            if i == len(points) - 2:
                # 这是一个标准的 P0 -> P1 -> P2 片段
                self._draw_quadratic_segment(p0, p1, p2)
                p0 = p2
                i += 1 # consumed p1
                # loop will end
            else:
                # 还有更多的点，说明 p2 也是控制点（off-curve）？
                # 不一定。
                # 实际上 fontTools 传递的 points 中，如果不含有隐式点，则中间的点都是 on-curve?
                # 不！qCurveTo 的语义是：points list 中，只有最后一个是 on-curve，其他的全是 off-curve。
                # 如果有连续 off-curve，中间加隐式点。
                
                # 正确逻辑：
                # points = [off, off, off, ..., on]
                
                next_p = points[i+1]
                
                # 当前 p1 是 off-curve.
                # 下一个 next_p 也是 off-curve (除非它是最后一个点)
                # 所以终点是中点
                
                mid_x = (p1[0] + next_p[0]) / 2.0
                mid_y = (p1[1] + next_p[1]) / 2.0
                mid = (mid_x, mid_y)
                
                self._draw_quadratic_segment(p0, p1, mid)
                p0 = mid
                i += 1
                
        # 处理最后一段（如果有剩余）
        # 上面的循环处理了所有连续 off-curve 的情况
        # 如果 loop 结束，i 指向最后一个点（它是 on-curve）
        # 或者是刚好处理完。
        
        # 让我们重新梳理：
        # 例子：P1(off), P2(off), P3(on)
        # i=0. p1=P1. i < len-1 (2).
        # next_p = P2.
        # draw P0->P1->Mid(P1,P2). P0=Mid. i=1.
        # i=1. p1=P2. i == len-2. (1 == 1). True.
        # draw P0->P2->P3. P0=P3. i=2.
        # loop ends. Correct.
        
        # 例子：P1(off), P2(on).
        # i=0. i == len-2 (0==0). True.
        # draw P0->P1->P2.
        # loop ends. Correct.
        
        self.current_point = points[-1]

    def _draw_quadratic_segment(self, p0, p1, p2):
        steps = 10
        for i in range(1, steps + 1):
            t = i / steps
            # Quadratic Bezier
            # B(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
            it = 1-t
            a = it*it
            b = 2*it*t
            c = t*t
            
            x = a * p0[0] + b * p1[0] + c * p2[0]
            y = a * p0[1] + b * p1[1] + c * p2[1]
            self.current_polygon.append((x, y))

    def _closePath(self):
        if self.current_polygon and len(self.current_polygon) >= 3:
            # 确保闭合
            if self.current_polygon[0] != self.current_polygon[-1]:
                self.current_polygon.append(self.current_polygon[0])
            
            try:
                poly = Polygon(self.current_polygon)
                if poly.is_valid:
                    self.polygons.append(poly)
                else:
                    # 尝试修复
                    clean_poly = poly.buffer(0)
                    if clean_poly.is_valid and not clean_poly.is_empty:
                         if isinstance(clean_poly, Polygon):
                             self.polygons.append(clean_poly)
                         elif isinstance(clean_poly, MultiPolygon):
                             for p in clean_poly.geoms:
                                 self.polygons.append(p)
            except Exception as e:
                print(f"创建多边形失败: {e}")
                pass
        self.current_polygon = []
        self.current_point = None
        
    def addComponent(self, glyphName, transformation):
        """处理组件引用"""
        try:
            glyph = self.glyphSet[glyphName]
            tPen = TransformPen(self, transformation)
            glyph.draw(tPen)
        except Exception as e:
            print(f"处理组件 {glyphName} 时出错: {e}")
    
    def get_geometry(self):
        """获取最终的几何图形（处理孔洞和重叠）"""
        self._closePath()
        
        if not self.polygons:
            return None

        from shapely.ops import unary_union
        
        # 预处理：修复无效多边形，移除太小的
        clean_polys = []
        for p in self.polygons:
            if not p.is_valid:
                p = p.buffer(0)
            if p.is_empty:
                continue
            if isinstance(p, MultiPolygon):
                clean_polys.extend(p.geoms)
            else:
                clean_polys.append(p)
                
        if not clean_polys:
            return None
            
        # 算法：构建包含层级树来识别孔洞
        # 1. 按面积从大到小排序（父节点一定比子节点大）
        clean_polys.sort(key=lambda x: x.area, reverse=True)
        
        # 结构：{'poly': polygon, 'holes': [], 'level': 0}
        # 这里简化处理：通常字体只要区分 实体(Level 0, 2...) 和 孔(Level 1, 3...)
        # 我们使用一个列表来存储根实心体
        roots = []
        
        for p in clean_polys:
            placed = False
            # 尝试放入现有的层级中
            # 这是一个简化的递归查找，实际上对于大多数平面字体，深度不会很深
            
            # 我们通过遍历树来找到 p 的父节点
            # 因为是已排序的，p 只能是之前某些节点的子节点
            
            # 使用栈进行非递归遍历查找最佳父节点
            # 实际上，我们需要找到包含 p 的“最小”节点 (most nested)
            
            best_parent = None
            parent_level = -1
            
            # 简单的两层检查（对于大多数情况足够：O, 8, 回）
            # 但为了通用性，我们做一个线性扫描来确定 p 的 nesting level
            # 这种方法对于 N 小 (N<100) 是飞快的
            
            # 统计 p 被多少个其他 poly 包含
            container_count = 0
            containers = []
            for other in clean_polys:
                if p is other: continue
                # 如果 other 包含 p (且 other 面积必须大于 p，已由排序保证)
                if other.contains(p):
                    container_count += 1
                    containers.append(other)
            
            # 根据 Even-Odd 规则
            # 0 containers -> Solid
            # 1 container  -> Hole
            # 2 containers -> Solid (Inner Island)
            # ...
            
            if container_count % 2 == 0:
                # 这是一个实体 (Solid)
                # 我们先把它暂存起来。
                # 后面构建时，我们会把它和它的孔洞配对。
                # 但这种分离方法很难组装 (parent, hole) 关系。
                pass
            
            # 让我们换一种思路：
            # 我们只关心构建合法的 Polygon(shell, holes)
            # 每一个 Even level poly 都是一个 shell。
            # 每一个 Odd level poly 都是最近的 Even parent 的 hole。
            pass
        
        # 重新实现的 Robust 算法：
        # 1. 计算每个 poly 的 nesting level
        # 2. Group holes with their immediate parents
        
        polys_with_level = []
        for i, p in enumerate(clean_polys):
            level = 0
            parent = None
            # 寻找直接父节点（包含 p 且面积最小的那个）
            min_area = float('inf')
            
            for j, potential_parent in enumerate(clean_polys):
                if i == j: continue
                if potential_parent.contains(p):
                    level += 1
                    if potential_parent.area < min_area:
                        min_area = potential_parent.area
                        parent = potential_parent
            
            polys_with_level.append({
                'poly': p,
                'level': level,
                'parent': parent,
                'holes': []
            })
            
        # 3. 将 Holes 分配给 Parents
        results = []
        
        # 字典映射 poly -> info
        poly_map = {id(info['poly']): info for info in polys_with_level}
        
        for info in polys_with_level:
            if info['level'] % 2 == 1:
                # 这是一个孔 (Hole)
                # 找到它的直接父节点 (必须是偶数层级的)
                # 注意：如果层级计算正确，Parent 的 level 应该是 level-1 (Even)
                if info['parent']:
                    parent_info = poly_map.get(id(info['parent']))
                    if parent_info:
                        parent_info['holes'].append(info['poly'])
                else:
                    # 异常情况：奇数层级但没有父节点？逻辑上不可能（除非相交导致 contains 失败）
                    # 当作实体处理
                    results.append(info['poly'])
            else:
                # 这是一个实体 (Solid) 的基础
                # 我们稍后会用它的 holes 构建它
                pass

        # 4. 构建最终 Polygons
        final_polys = []
        for info in polys_with_level:
            if info['level'] % 2 == 0:
                # Solid
                shell = info['poly'].exterior
                holes = [h.exterior for h in info['holes']]
                try:
                    new_poly = Polygon(shell=shell, holes=holes)
                    if new_poly.is_valid:
                        final_polys.append(new_poly)
                    else:
                        final_polys.append(new_poly.buffer(0))
                except:
                    final_polys.append(info['poly']) # Fallback

        if not final_polys:
            return None
            
        # 5. 最后合并所有实体（处理组件重叠）
        try:
            return unary_union(final_polys)
        except Exception as e:
            print(f"合并最终多边形失败: {e}")
            return MultiPolygon(final_polys)


def extract_glyph_outline(font_path: str, character: str) -> tuple:
    """
    从字体文件提取字符轮廓
    
    支持单个字符和多字符字符串（如 "Shift"、"Win"、"Fn"）
    对于多字符字符串，会将所有字符水平排列
    """
    try:
        font = TTFont(font_path)
        glyph_set = font.getGlyphSet()
        
        # 如果字符串长度大于1，需要处理多个字符
        if len(character) > 1:
            return _extract_multichar_outline(font, glyph_set, character)
        
        # 单个字符的处理（原有逻辑）
        # 获取字符的glyph名称
        # 增强的 cmap 查找
        cmap = font.getBestCmap()
        char_code = ord(character)
        
        if char_code not in cmap:
            # 尝试查找备用 cmap
            found = False
            for table in font['cmap'].tables:
                if char_code in table.cmap:
                    cmap = table.cmap
                    found = True
                    break
            if not found:
                print(f"字符 '{character}' (U+{char_code:04X}) 在字体中未找到")
                return None, None
        
        glyph_name = cmap[char_code]
        glyph = glyph_set[glyph_name]
        
        # 使用ShapelyPen提取轮廓
        pen = ShapelyPen(glyph_set)
        glyph.draw(pen)
        
        geometry = pen.get_geometry()
        
        if geometry is None:
            print(f"提取的几何图形为空 (Glyph: {glyph_name})")
            return None, None
        
        # 获取边界框
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        
        return geometry, bounds
        
    except Exception as e:
        print(f"提取字体轮廓时出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def _extract_multichar_outline(font, glyph_set, text: str) -> tuple:
    """
    提取多字符字符串的轮廓
    
    参数:
        font: TTFont 对象
        glyph_set: 字体字形集合
        text: 多字符字符串
    
    返回:
        (合并后的几何图形, 边界框)
    """
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union
    from shapely.affinity import translate
    
    char_geometries = []
    current_x = 0.0
    
    for char in text:
        try:
            char_code = ord(char)
            # 每个字符重新查找 cmap，避免上一字符使用的子集 cmap 导致本字符遗漏（对中文等多 Unicode 区块重要）
            cmap = font.getBestCmap()
            if char_code not in cmap:
                found = False
                for table in font['cmap'].tables:
                    if char_code in table.cmap:
                        cmap = table.cmap
                        found = True
                        break
                if not found:
                    print(f"字符 '{char}' (U+{char_code:04X}) 在字体中未找到，跳过（请选用含该字符的字体，如思源黑体、Noto Sans CJK）")
                    continue
            
            glyph_name = cmap[char_code]
            glyph = glyph_set[glyph_name]
            
            # 提取字符轮廓
            pen = ShapelyPen(glyph_set)
            glyph.draw(pen)
            char_geometry = pen.get_geometry()
            
            if char_geometry is None:
                continue
            
            # 获取字符边界框以计算字符宽度
            char_bounds = char_geometry.bounds  # (minx, miny, maxx, maxy)
            char_width = char_bounds[2] - char_bounds[0]
            
            # 将字符移动到当前位置（水平排列）
            # 需要先平移到原点，然后移动到目标位置
            offset_x = current_x - char_bounds[0]  # 左对齐
            char_geometry = translate(char_geometry, xoff=offset_x, yoff=0)
            
            char_geometries.append(char_geometry)
            
            # 更新下一个字符的x位置（字符宽度 + 小间距，通常约为字符宽度的10-20%）
            spacing = char_width * 0.15  # 15% 的字符宽度作为间距
            current_x += char_width + spacing
            
        except Exception as e:
            print(f"处理字符 '{char}' 时出错: {e}")
            continue
    
    if not char_geometries:
        return None, None
    
    # 合并所有字符的几何图形
    try:
        merged_geometry = unary_union(char_geometries)
        bounds = merged_geometry.bounds
        return merged_geometry, bounds
    except Exception as e:
        print(f"合并多字符几何图形失败: {e}")
        # 如果合并失败，返回第一个字符的几何图形
        if char_geometries:
            bounds = char_geometries[0].bounds
            return char_geometries[0], bounds
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
