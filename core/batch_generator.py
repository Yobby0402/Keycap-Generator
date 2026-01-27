"""
批量生成器
将 KLE 按键列表转换为 3D 模型
"""
from typing import List, Tuple, Optional
import cadquery as cq
from core.kle_parser import KLEKey
from core.parameters import KeycapDesign, KeycapGeometry, TextParameters
from core.keycap_modeler import KeycapModeler
from core.legend_mapping import LegendMapping, convert_kle_label_to_text_params, get_top_surface_size
from core.keycap_presets import u_to_mm

class BatchGenerator:
    """批量生成器"""
    
    def __init__(self, global_geometry: KeycapGeometry, legend_mapping: LegendMapping):
        """
        初始化批量生成器
        
        参数:
            global_geometry: 全局几何参数（所有按键共用）
            legend_mapping: 字符样式映射配置
        """
        self.global_geometry = global_geometry
        self.legend_mapping = legend_mapping
        self.default_font_path = None  # 可以从单键模式获取
    
    def set_default_font(self, font_path: str):
        """设置默认字体路径"""
        self.default_font_path = font_path
    
    def convert_kle_key_to_design(self, kle_key: KLEKey) -> KeycapDesign:
        """
        将 KLEKey 转换为 KeycapDesign
        
        参数:
            kle_key: KLE 按键数据
        
        返回:
            KeycapDesign 对象
        """
        # 创建几何参数（基于全局几何，但使用 KLE 的尺寸）
        stabilizer_enabled = getattr(self.global_geometry, 'stabilizer_enabled', False)
        stabilizer_length = getattr(self.global_geometry, 'stabilizer_length', 50.0)
        print(f"【批量生成】卫星轴参数: enabled={stabilizer_enabled}, length={stabilizer_length}mm")
        print(f"  - global_geometry类型: {type(self.global_geometry)}")
        print(f"  - hasattr(global_geometry, 'stabilizer_enabled'): {hasattr(self.global_geometry, 'stabilizer_enabled')}")
        
        geometry = KeycapGeometry(
            key_width=u_to_mm(kle_key.width) if kle_key.width > 0 else self.global_geometry.key_width,
            key_height=u_to_mm(kle_key.height) if kle_key.height > 0 else self.global_geometry.key_height,
            key_depth=self.global_geometry.key_depth,
            key_width_u=kle_key.width,
            key_height_u=kle_key.height,
            use_u_units=True,
            height_profile=self.global_geometry.height_profile,
            keycap_row=self.global_geometry.keycap_row,
            side_angle=self.global_geometry.side_angle,
            wall_thickness=self.global_geometry.wall_thickness,
            top_thickness=self.global_geometry.top_thickness,
            edge_profile_mode=getattr(self.global_geometry, 'edge_profile_mode', "fillet"),
            edge_profile_radius=getattr(self.global_geometry, 'edge_profile_radius', 0.0),
            edge_profile_outer=getattr(self.global_geometry, 'edge_profile_outer', True),
            edge_profile_inner=getattr(self.global_geometry, 'edge_profile_inner', False),
            edge_profile_left=getattr(self.global_geometry, 'edge_profile_left', True),
            edge_profile_right=getattr(self.global_geometry, 'edge_profile_right', True),
            edge_profile_top=getattr(self.global_geometry, 'edge_profile_top', True),
            edge_profile_bottom=getattr(self.global_geometry, 'edge_profile_bottom', True),
            corner_radius=self.global_geometry.corner_radius,
            stem_type=self.global_geometry.stem_type,
            stem_enabled=self.global_geometry.stem_enabled,
            stem_height=self.global_geometry.stem_height,
            stem_cylinder_diameter=self.global_geometry.stem_cylinder_diameter,
            stem_cross_width=self.global_geometry.stem_cross_width,
            stem_cross_length=self.global_geometry.stem_cross_length,
            stabilizer_enabled=stabilizer_enabled,
            stabilizer_length=stabilizer_length,
            curved_top_enabled=getattr(self.global_geometry, 'curved_top_enabled', False),
            curved_top_x_enabled=getattr(self.global_geometry, 'curved_top_x_enabled', False),
            curved_top_y_enabled=getattr(self.global_geometry, 'curved_top_y_enabled', False),
            curved_top_x_radius=getattr(self.global_geometry, 'curved_top_x_radius', 90.0),
            curved_top_y_radius=getattr(self.global_geometry, 'curved_top_y_radius', 90.0),
            curved_top_direction=getattr(self.global_geometry, 'curved_top_direction', 'convex')
        )
        print(f"  - 创建的geometry.stabilizer_enabled: {geometry.stabilizer_enabled}")
        print(f"  - 创建的geometry.stabilizer_length: {geometry.stabilizer_length}")
        
        # 转换字符（按顶面尺寸放置，避免侧面倾角导致字符超出顶面）
        text_items = []
        key_width_mm = u_to_mm(kle_key.width)
        key_height_mm = u_to_mm(kle_key.height)
        key_depth = self.global_geometry.key_depth
        side_angle = getattr(self.global_geometry, 'side_angle', 0.0) or 0.0
        top_w, top_h = get_top_surface_size(key_width_mm, key_height_mm, key_depth, side_angle)
        
        for pos_idx, label_text in enumerate(kle_key.labels):
            if label_text and label_text.strip():
                text_param = convert_kle_label_to_text_params(
                    label_text=label_text,
                    position_index=pos_idx,
                    legend_mapping=self.legend_mapping,
                    default_font_path=self.default_font_path,
                    key_width=key_width_mm,
                    key_height=key_height_mm,
                    top_width=top_w,
                    top_height=top_h
                )
                if text_param:
                    # 确保字体路径已设置（使用默认字体或Times New Roman）
                    if not text_param.font_path:
                        if self.default_font_path:
                            text_param.font_path = self.default_font_path
                        else:
                            # 如果默认字体也没有，使用Times New Roman
                            from utils.font_utils import find_times_new_roman
                            text_param.font_path = find_times_new_roman()
                    text_items.append(text_param)
        
        # 创建设计对象
        design = KeycapDesign(geometry=geometry, text_items=text_items)
        return design
    
    def generate_single_key(self, kle_key: KLEKey) -> Tuple[Optional[cq.Workplane], Optional[cq.Workplane]]:
        """
        生成单个按键的 3D 模型
        
        参数:
            kle_key: KLE 按键数据
        
        返回:
            (keycap_model, text_model) 或 (None, None) 如果失败
        """
        try:
            design = self.convert_kle_key_to_design(kle_key)
            modeler = KeycapModeler(design)
            keycap_model, text_model, _ = modeler.generate()  # 忽略 image_inlay
            return keycap_model, text_model
        except Exception as e:
            print(f"生成按键失败 (位置 {kle_key.x:.1f}, {kle_key.y:.1f}): {e}")
            return None, None
    
    def generate_all_keys(self, kle_keys: List[KLEKey], 
                         progress_callback=None) -> List[Tuple[Optional[cq.Workplane], Optional[cq.Workplane]]]:
        """
        批量生成所有按键的 3D 模型
        
        参数:
            kle_keys: KLE 按键列表
            progress_callback: 进度回调函数 (current, total) -> None
        
        返回:
            模型列表，每个元素是 (keycap_model, text_model)
        """
        results = []
        total = len(kle_keys)
        
        for i, kle_key in enumerate(kle_keys):
            if progress_callback:
                progress_callback(i + 1, total)
            
            keycap_model, text_model = self.generate_single_key(kle_key)
            results.append((keycap_model, text_model))
        
        return results
