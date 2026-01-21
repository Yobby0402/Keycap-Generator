"""
批量编辑Tab界面
包含按键类型树、编辑面板和预览
"""
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.key_type_tree_widget import KeyTypeTreeWidget
from ui.batch_edit_panel import BatchEditPanel
from ui.batch_edit_preview_2d import BatchEditPreview2D
from ui.preview_widget import PreviewWidget
from core.key_type_analyzer import KeyTypeAnalyzer, KeyTypeSignature
from core.batch_edit_config import BatchEditConfig
from core.parameters import KeycapGeometry
from core.legend_mapping import LegendMapping, LegendStyle, _calculate_base_position
from core.keycap_presets import u_to_mm
from typing import Dict, List, Optional
from core.kle_parser import KLEKey


class BatchEditTab(QWidget):
    """批量编辑Tab界面"""
    
    # 信号：配置已保存并应用到所有匹配按键
    config_applied = pyqtSignal(dict)  # {类型标识: BatchEditConfig}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kle_keys: List[KLEKey] = []
        self.type_map: Dict[str, List[int]] = {}
        self.configs: Dict[str, BatchEditConfig] = {}  # {类型标识: BatchEditConfig}
        self.current_type_id: Optional[str] = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 左侧：按键类型树
        self.type_tree = KeyTypeTreeWidget()
        self.type_tree.type_selected.connect(self.on_type_selected)
        layout.addWidget(self.type_tree, stretch=1)
        
        # 中间：编辑区域（上下布局）
        edit_widget = QWidget()
        edit_layout = QVBoxLayout(edit_widget)
        edit_layout.setSpacing(5)
        
        # 参数面板
        self.edit_panel = BatchEditPanel()
        self.edit_panel.config_saved.connect(self.on_config_saved)
        self.edit_panel.config_changed.connect(self.on_config_changed)  # 实时预览
        edit_layout.addWidget(self.edit_panel, stretch=1)
        
        # 预览区域（左右布局）
        preview_splitter = QSplitter(Qt.Horizontal)
        
        # 2D预览
        self.preview_2d = BatchEditPreview2D()
        self.preview_2d.position_changed.connect(self.on_text_position_changed)
        preview_splitter.addWidget(self.preview_2d)
        
        # 3D预览
        self.preview_3d = PreviewWidget()
        preview_splitter.addWidget(self.preview_3d)
        
        preview_splitter.setStretchFactor(0, 1)
        preview_splitter.setStretchFactor(1, 1)
        edit_layout.addWidget(preview_splitter, stretch=2)
        
        layout.addWidget(edit_widget, stretch=2)
    
    def load_kle_keys(self, keys: List[KLEKey], default_geometry: KeycapGeometry, 
                      default_font_path: Optional[str] = None):
        """
        加载KLE按键列表
        
        参数:
            keys: KLE 按键列表
            default_geometry: 默认几何参数
            default_font_path: 默认字体路径
        """
        self.kle_keys = keys
        # 设置默认字体到编辑面板
        self.edit_panel.set_default_font(default_font_path)
        
        # 分析按键类型
        self.type_map = KeyTypeAnalyzer.analyze_keys(keys)
        
        # 更新树状列表
        self.type_tree.load_key_types(self.type_map)
        
        # 为每个类型创建默认配置
        legend_mapping = LegendMapping.create_default()
        if default_font_path:
            for style in legend_mapping.mapping.values():
                if style.font_path is None:
                    style.font_path = default_font_path
        
        for type_id, indices in self.type_map.items():
            if type_id not in self.configs:
                # 创建默认配置
                # 从第一个按键获取实际尺寸
                if indices:
                    first_key = keys[indices[0]]
                    key_width_mm = u_to_mm(first_key.width)
                    key_height_mm = u_to_mm(first_key.height)
                else:
                    key_width_mm = default_geometry.key_width
                    key_height_mm = default_geometry.key_height
                
                # 解析类型标识获取宽度和位置
                key_type = self._parse_type_id(type_id)
                if key_type:
                    # key_type.width 已经是 u 单位，不需要转换
                    
                    config = BatchEditConfig(
                        key_type=key_type,
                        geometry=KeycapGeometry(
                            key_width=key_width_mm,
                            key_height=key_height_mm,
                            key_depth=default_geometry.key_depth,
                            side_angle=default_geometry.side_angle,
                            corner_radius=default_geometry.corner_radius,
                            wall_thickness=default_geometry.wall_thickness,
                            top_thickness=default_geometry.top_thickness,
                            edge_profile_mode=getattr(default_geometry, 'edge_profile_mode', "fillet"),
                            edge_profile_radius=getattr(default_geometry, 'edge_profile_radius', 0.0),
                            edge_profile_outer=getattr(default_geometry, 'edge_profile_outer', True),
                            edge_profile_inner=getattr(default_geometry, 'edge_profile_inner', False),
                            edge_profile_left=getattr(default_geometry, 'edge_profile_left', True),
                            edge_profile_right=getattr(default_geometry, 'edge_profile_right', True),
                            edge_profile_top=getattr(default_geometry, 'edge_profile_top', True),
                            edge_profile_bottom=getattr(default_geometry, 'edge_profile_bottom', True),
                            stem_enabled=default_geometry.stem_enabled,
                            stem_height=default_geometry.stem_height,
                            stem_cylinder_diameter=default_geometry.stem_cylinder_diameter,
                            stem_cross_width=default_geometry.stem_cross_width,
                            stem_cross_length=default_geometry.stem_cross_length,
                            stabilizer_enabled=getattr(default_geometry, 'stabilizer_enabled', False),
                            stabilizer_length=getattr(default_geometry, 'stabilizer_length', 50.0)
                        )
                    )
                    
                    # 为每个位置设置默认样式
                    for pos_idx in key_type.label_positions:
                        style = legend_mapping.get_style(pos_idx, default_font_path)
                        config.set_style_for_position(pos_idx, style)
                    
                    self.configs[type_id] = config
    
    def _parse_type_id(self, type_id: str) -> Optional[KeyTypeSignature]:
        """解析类型标识字符串"""
        try:
            # 例如 "1u_0-9" -> width=1.0u, positions={0, 9}
            parts = type_id.split('u_', 1)
            if len(parts) != 2:
                return None
            
            width_u = float(parts[0])
            pos_str = parts[1]
            
            if pos_str == "empty":
                positions = set()
            else:
                positions = {int(p) for p in pos_str.split('-')}
            
            # 高度默认为1.0u（KLE中通常相同）
            return KeyTypeSignature(width=width_u, height=1.0, label_positions=positions)
        except (ValueError, IndexError):
            return None
    
    def on_type_selected(self, type_id: str):
        """处理类型选择"""
        self.current_type_id = type_id
        
        if type_id not in self.configs:
            return
        
        config = self.configs[type_id]
        
        # 更新编辑面板
        self.edit_panel.load_type(config.key_type, config)
        
        # 更新预览
        self.preview_2d.update_preview(config.key_type, config)
        
        # 更新3D预览
        self._update_3d_preview(config)
    
    def on_config_changed(self, config: BatchEditConfig):
        """处理配置改变（实时预览）"""
        if config and config.key_type:
            # 实时更新2D预览
            self.preview_2d.update_preview(config.key_type, config)
            
            # 实时更新3D预览
            self._update_3d_preview(config)
    
    def _update_3d_preview(self, config: BatchEditConfig):
        """更新3D预览"""
        try:
            from core.batch_generator import BatchGenerator
            from core.legend_mapping import LegendMapping, convert_kle_label_to_text_params
            from core.parameters import KeycapDesign, TextParameters, KeycapGeometry
            from core.keycap_modeler import KeycapModeler
            from core.keycap_presets import u_to_mm
            
            # 创建临时KeycapDesign（字符用X代替）
            # 注意：不要直接修改config.geometry，而是创建一个副本
            stabilizer_enabled = getattr(config.geometry, 'stabilizer_enabled', False)
            stabilizer_length = getattr(config.geometry, 'stabilizer_length', 50.0)
            print(f"【批量编辑3D预览】卫星轴参数: enabled={stabilizer_enabled}, length={stabilizer_length}mm")
            
            geometry = KeycapGeometry(
                key_width=u_to_mm(config.key_type.width),
                key_height=u_to_mm(config.key_type.height),
                key_depth=config.geometry.key_depth,
                side_angle=config.geometry.side_angle,
                corner_radius=config.geometry.corner_radius,
                wall_thickness=config.geometry.wall_thickness,
                top_thickness=config.geometry.top_thickness,
                edge_profile_mode=getattr(config.geometry, 'edge_profile_mode', "fillet"),
                edge_profile_radius=getattr(config.geometry, 'edge_profile_radius', 0.0),
                edge_profile_outer=getattr(config.geometry, 'edge_profile_outer', True),
                edge_profile_inner=getattr(config.geometry, 'edge_profile_inner', False),
                edge_profile_left=getattr(config.geometry, 'edge_profile_left', True),
                edge_profile_right=getattr(config.geometry, 'edge_profile_right', True),
                edge_profile_top=getattr(config.geometry, 'edge_profile_top', True),
                edge_profile_bottom=getattr(config.geometry, 'edge_profile_bottom', True),
                stem_enabled=config.geometry.stem_enabled,
                stem_height=config.geometry.stem_height,
                stem_cylinder_diameter=config.geometry.stem_cylinder_diameter,
                stem_cross_width=config.geometry.stem_cross_width,
                stem_cross_length=config.geometry.stem_cross_length,
                stabilizer_enabled=stabilizer_enabled,
                stabilizer_length=stabilizer_length
            )
            
            # 创建TextParameters（字符用X代替）
            text_items = []
            key_width_mm = geometry.key_width
            key_height_mm = geometry.key_height
            
            for pos_idx in config.key_type.label_positions:
                style = config.get_style_for_position(pos_idx)
                base_x, base_y = _calculate_base_position(pos_idx, key_width_mm, key_height_mm)
                
                text_param = TextParameters(
                    text="X",
                    font_path=style.font_path,
                    size=style.size,
                    depth=style.depth,
                    offset_x=base_x + style.offset_x,
                    offset_y=base_y + style.offset_y
                )
                text_items.append(text_param)
            
            # 创建设计对象
            design = KeycapDesign(geometry=geometry, text_items=text_items)
            
            # 生成模型
            modeler = KeycapModeler(design)
            keycap_model, text_model = modeler.generate()
            
            # 更新3D预览
            if keycap_model:
                self.preview_3d.update_model(keycap_model, text_model)
        except Exception as e:
            print(f"生成3D预览失败: {e}")
            import traceback
            traceback.print_exc()
    
    def on_text_position_changed(self, pos_idx: int, offset_x: float, offset_y: float):
        """文字位置改变（拖动时）"""
        # 实时更新3D预览
        if self.current_type_id and self.current_type_id in self.configs:
            config = self.configs[self.current_type_id]
            self._update_3d_preview(config)
    
    def on_config_saved(self, config: BatchEditConfig):
        """处理配置保存"""
        if self.current_type_id:
            # 更新配置
            self.configs[self.current_type_id] = config
            
            # 更新预览
            self.preview_2d.update_preview(config.key_type, config)
            self._update_3d_preview(config)
            
            # 应用到所有该类型的按键
            self._apply_config_to_keys(self.current_type_id, config)
            
            # 发出信号，通知配置已应用（只发送当前应用的配置）
            applied_configs = {self.current_type_id: config}
            self.config_applied.emit(applied_configs)
    
    def _apply_config_to_keys(self, type_id: str, config: BatchEditConfig):
        """
        将配置应用到所有匹配该类型的按键
        
        注意：这里不直接修改KLEKey对象，而是将配置存储起来，
        供生成3D模型时使用。KLEKey的labels等原始数据保持不变。
        """
        if type_id not in self.type_map:
            return
        
        # 获取所有匹配该类型的按键索引
        key_indices = self.type_map[type_id]
        
        print(f"应用配置到 {len(key_indices)} 个按键 (类型: {type_id})")
        print(f"  - 几何参数: 深度={config.geometry.key_depth:.1f}mm, "
              f"侧面斜角={config.geometry.side_angle:.1f}°, "
              f"圆角={config.geometry.corner_radius:.2f}mm")
        print(f"  - 字符样式位置数: {len(config.text_styles)}")
    
    def get_configs(self) -> Dict[str, BatchEditConfig]:
        """获取所有配置（供外部访问）"""
        return self.configs.copy()
    
    def get_config_for_key(self, key: KLEKey) -> Optional[BatchEditConfig]:
        """
        获取指定按键对应的配置
        
        参数:
            key: KLE 按键
        
        返回:
            BatchEditConfig 或 None（如果找不到匹配的配置）
        """
        # 获取按键的类型签名
        key_type = KeyTypeAnalyzer.get_signature_for_key(key)
        type_id = key_type.to_string()
        
        # 返回对应的配置
        return self.configs.get(type_id)
