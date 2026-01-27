"""
键盘参数 Tab 界面
左：按键类型树；中：对应类型参数；右：2D/3D 预览 + 保存并应用、恢复到默认参数
"""
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QSplitter, QPushButton, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
from ui.key_type_tree_widget import KeyTypeTreeWidget
from ui.batch_edit_panel import BatchEditPanel
from ui.batch_edit_preview_2d import BatchEditPreview2D
from ui.preview_widget import PreviewWidget
from core.key_type_analyzer import KeyTypeAnalyzer, KeyTypeSignature
from core.batch_edit_config import BatchEditConfig
from core.parameters import KeycapGeometry
from core.legend_mapping import LegendMapping, LegendStyle, _calculate_base_position, get_top_surface_size
from core.keycap_presets import u_to_mm
from typing import Dict, List, Optional
from core.kle_parser import KLEKey


class BatchEditTab(QWidget):
    """键盘参数 Tab 界面（左：类型树；中：参数；右：2D/3D/保存/恢复）"""
    
    # 信号：配置已保存并应用到所有匹配按键
    config_applied = pyqtSignal(dict)  # {类型标识: BatchEditConfig}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kle_keys: List[KLEKey] = []
        self.type_map: Dict[str, List[int]] = {}
        self.configs: Dict[str, BatchEditConfig] = {}  # {类型标识: BatchEditConfig}
        self.current_type_id: Optional[str] = None
        self.default_geometry: Optional[KeycapGeometry] = None
        self.default_font_path: Optional[str] = None
        self.setup_ui()
    
    def setup_ui(self):
        """左中右布局：左=类型树，中=参数，右=2D(40%)/3D(40%)/保存(10%)/恢复(10%)"""
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 左侧：按键类型树
        self.type_tree = KeyTypeTreeWidget()
        self.type_tree.type_selected.connect(self.on_type_selected)
        layout.addWidget(self.type_tree, stretch=1)
        
        # 中间：对应类型的参数面板（不显示内置保存按钮，按钮在右侧列）
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        self.edit_panel = BatchEditPanel()
        self.edit_panel.set_show_save_button(False)
        self.edit_panel.config_saved.connect(self.on_config_saved)
        self.edit_panel.config_changed.connect(self.on_config_changed)
        center_scroll = QScrollArea()
        center_scroll.setWidgetResizable(True)
        center_scroll.setWidget(self.edit_panel)
        center_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        center_layout.addWidget(center_scroll)
        layout.addWidget(center_widget, stretch=1)
        
        # 右侧列：2D(4) : 3D(4) : 保存(1) : 恢复(1)
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        self.preview_2d = BatchEditPreview2D()
        self.preview_2d.position_changed.connect(self.on_text_position_changed)
        right_col.addWidget(self.preview_2d, stretch=4)
        self.preview_3d = PreviewWidget()
        right_col.addWidget(self.preview_3d, stretch=4)
        save_btn = QPushButton("保存并应用")
        save_btn.setStyleSheet("font-weight: bold; padding: 10px;")
        save_btn.clicked.connect(self.edit_panel.save_and_apply)
        right_col.addWidget(save_btn, stretch=1)
        reset_btn = QPushButton("恢复到默认参数")
        reset_btn.setStyleSheet("padding: 10px;")
        reset_btn.clicked.connect(self._reset_current_to_default)
        right_col.addWidget(reset_btn, stretch=1)
        right_wrap = QWidget()
        right_wrap.setLayout(right_col)
        layout.addWidget(right_wrap, stretch=1)
    
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
        self.default_geometry = default_geometry
        self.default_font_path = default_font_path
        self.edit_panel.set_default_font(default_font_path)
        
        self.type_map = KeyTypeAnalyzer.analyze_keys(keys)
        self.type_tree.load_key_types(self.type_map)
        
        for type_id in self.type_map:
            if type_id not in self.configs:
                cfg = self._create_default_config_for_type(type_id)
                if cfg:
                    self.configs[type_id] = cfg
    
    def _create_default_config_for_type(self, type_id: str) -> Optional[BatchEditConfig]:
        """为指定类型创建默认配置（用于初次加载与“恢复到默认参数”）"""
        dg = self.default_geometry
        dfont = self.default_font_path
        if not dg or not self.kle_keys:
            return None
        indices = self.type_map.get(type_id, [])
        if indices:
            first_key = self.kle_keys[indices[0]]
            key_width_mm = u_to_mm(first_key.width)
            key_height_mm = u_to_mm(first_key.height)
        else:
            key_width_mm = dg.key_width
            key_height_mm = dg.key_height
        key_type = self._parse_type_id(type_id)
        if not key_type:
            return None
        legend_mapping = LegendMapping.create_default()
        if dfont:
            for style in legend_mapping.mapping.values():
                if style.font_path is None:
                    style.font_path = dfont
        config = BatchEditConfig(
            key_type=key_type,
            geometry=KeycapGeometry(
                key_width=key_width_mm,
                key_height=key_height_mm,
                key_depth=dg.key_depth,
                side_angle=dg.side_angle,
                corner_radius=dg.corner_radius,
                wall_thickness=dg.wall_thickness,
                top_thickness=dg.top_thickness,
                edge_profile_mode=getattr(dg, 'edge_profile_mode', "fillet"),
                edge_profile_radius=getattr(dg, 'edge_profile_radius', 0.0),
                edge_profile_outer=getattr(dg, 'edge_profile_outer', True),
                edge_profile_inner=getattr(dg, 'edge_profile_inner', False),
                edge_profile_left=getattr(dg, 'edge_profile_left', True),
                edge_profile_right=getattr(dg, 'edge_profile_right', True),
                edge_profile_top=getattr(dg, 'edge_profile_top', True),
                edge_profile_bottom=getattr(dg, 'edge_profile_bottom', True),
                stem_enabled=dg.stem_enabled,
                stem_height=dg.stem_height,
                stem_cylinder_diameter=dg.stem_cylinder_diameter,
                stem_cross_width=dg.stem_cross_width,
                stem_cross_length=dg.stem_cross_length,
                stabilizer_enabled=getattr(dg, 'stabilizer_enabled', False),
                stabilizer_length=getattr(dg, 'stabilizer_length', 50.0),
                curved_top_enabled=getattr(dg, 'curved_top_enabled', False),
                curved_top_x_enabled=getattr(dg, 'curved_top_x_enabled', False),
                curved_top_y_enabled=getattr(dg, 'curved_top_y_enabled', False),
                curved_top_x_radius=getattr(dg, 'curved_top_x_radius', 90.0),
                curved_top_y_radius=getattr(dg, 'curved_top_y_radius', 90.0),
                curved_top_direction=getattr(dg, 'curved_top_direction', 'convex')
            )
        )
        for pos_idx in key_type.label_positions:
            style = legend_mapping.get_style(pos_idx, dfont)
            config.set_style_for_position(pos_idx, style)
        return config
    
    def _reset_current_to_default(self):
        """将当前选中类型的参数恢复为默认，并刷新预览、发出应用信号"""
        if not self.current_type_id or not self.default_geometry or not self.kle_keys:
            return
        cfg = self._create_default_config_for_type(self.current_type_id)
        if not cfg:
            return
        self.configs[self.current_type_id] = cfg
        self.edit_panel.load_type(cfg.key_type, cfg)
        self.preview_2d.update_preview(cfg.key_type, cfg)
        self._update_3d_preview(cfg)
        self.config_applied.emit({self.current_type_id: cfg})
    
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
                stabilizer_length=stabilizer_length,
                curved_top_enabled=getattr(config.geometry, 'curved_top_enabled', False),
                curved_top_x_enabled=getattr(config.geometry, 'curved_top_x_enabled', False),
                curved_top_y_enabled=getattr(config.geometry, 'curved_top_y_enabled', False),
                curved_top_x_radius=getattr(config.geometry, 'curved_top_x_radius', 90.0),
                curved_top_y_radius=getattr(config.geometry, 'curved_top_y_radius', 90.0),
                curved_top_direction=getattr(config.geometry, 'curved_top_direction', 'convex')
            )
            
            # 创建TextParameters（字符用X代替）；按顶面尺寸放置，避免超出顶面
            text_items = []
            key_width_mm = geometry.key_width
            key_height_mm = geometry.key_height
            top_w, top_h = get_top_surface_size(
                key_width_mm, key_height_mm,
                geometry.key_depth,
                getattr(geometry, 'side_angle', 0.0) or 0.0
            )
            for pos_idx in config.key_type.label_positions:
                style = config.get_style_for_position(pos_idx)
                base_x, base_y = _calculate_base_position(
                    pos_idx, key_width_mm, key_height_mm,
                    top_width=top_w, top_height=top_h
                )
                
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
            
            # 生成模型（返回 keycap_body, text_model, image_inlay，3D 预览只用前两项）
            modeler = KeycapModeler(design)
            keycap_model, text_model, _ = modeler.generate()
            
            # 更新3D预览
            if keycap_model:
                self.preview_3d.update_model(keycap_model, text_model)
        except Exception as e:
            print(f"生成3D预览失败: {e}")
            import traceback
            traceback.print_exc()
    
    def on_text_position_changed(self, pos_idx: int, offset_x: float, offset_y: float):
        """文字位置改变（拖动时）"""
        if not self.current_type_id or self.current_type_id not in self.configs:
            return
        config = self.configs[self.current_type_id]
        # 先把拖动得到的最新偏移写回当前类型的 config，再刷新 3D，避免 2D 的 config 与 configs 不同步导致拖动中 3D 错位
        from core.legend_mapping import LegendStyle
        style = config.get_style_for_position(pos_idx)
        config.set_style_for_position(pos_idx, LegendStyle(
            font_path=style.font_path,
            size=style.size,
            offset_x=offset_x,
            offset_y=offset_y,
            depth=style.depth,
            rotation=getattr(style, 'rotation', 0.0)
        ))
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
