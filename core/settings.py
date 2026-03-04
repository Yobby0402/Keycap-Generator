"""
设置管理
保存和加载软件设置
"""
import json
import os
import sys
import shutil
from pathlib import Path
from typing import Any, Dict


class Settings:
    """设置管理类"""
    
    def __init__(self, config_file: str = "config.json"):
        # 支持PyInstaller打包后的路径
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境：config.json保存在exe所在目录
            exe_dir = os.path.dirname(sys.executable)
            self.config_file = os.path.join(exe_dir, config_file)
            # 如果exe目录下没有config.json，尝试从资源中复制
            if not os.path.exists(self.config_file):
                # 尝试从临时资源目录复制
                if hasattr(sys, '_MEIPASS'):
                    resource_config = os.path.join(sys._MEIPASS, config_file)
                    if os.path.exists(resource_config):
                        shutil.copy2(resource_config, self.config_file)
        else:
            # 开发环境：使用当前目录
            self.config_file = config_file
        
        self.settings: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """加载设置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"加载设置失败: {e}")
                self.settings = {}
        else:
            # 默认设置
            self.settings = {
                "snap_enabled": True,
                "snap_grid_size": 1.0,
                "default_font_path": None,
                "default_key_size": "1u",
                "default_height_profile": "Cherry高度",
                "default_row": "R3",
                # 默认按键参数
                "default_side_angle": 0.0,
                "side_angle_step": 0.5,
                "default_wall_thickness": 1.0,
                "wall_thickness_step": 0.1,
                "default_stroke_width": 0.0,
                "stroke_width_step": 0.05,
                "default_edge_profile_mode": "fillet",
                "default_edge_profile_radius": 0.0,
                "edge_radius_step": 0.05,
                "default_edge_profile_outer": True,
                "default_edge_profile_inner": False,
                "default_edge_profile_left": True,
                "default_edge_profile_right": True,
                "default_edge_profile_top": True,
                "default_edge_profile_bottom": True,
                "default_text_height": 3.0,
                "text_height_step": 0.1,
                "default_text_depth": 0.5,
                "text_depth_step": 0.05,
                # 连接器/十字轴默认参数
                "default_stem_cross_width": 1.3,
                "default_stem_cross_length": 4.0,
                "default_stem_height": 4.0,
                "default_stem_cylinder_diameter": 5.4,
                "default_stem_enabled": True,
                "default_stem_type": "MX",
                "default_top_thickness": 1.0,
                "default_corner_radius": 0.5,
                # 弧面默认
                "default_curved_top_enabled": False,
                "default_curved_top_x_enabled": False,
                "default_curved_top_y_enabled": False,
                "default_curved_top_x_radius": 90.0,
                "default_curved_top_y_radius": 90.0,
                "default_curved_top_direction": "convex",
                # 卫星轴默认
                "default_stabilizer_enabled": False,
                "default_stabilizer_length": 50.0,
                "default_stabilizer_cross_width": 1.3,
                "default_stabilizer_cross_length": 4.0,
                "default_stabilizer_cylinder_diameter": 4.0,
                "default_stabilizer_depth": 5.0,
            }
            self.save()
    
    def save(self):
        """保存设置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存设置失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置值"""
        self.settings[key] = value
        self.save()
    
    def get_snap_enabled(self) -> bool:
        """获取对齐是否启用"""
        return self.get("snap_enabled", True)
    
    def set_snap_enabled(self, enabled: bool):
        """设置对齐是否启用"""
        self.set("snap_enabled", enabled)
    
    def get_snap_grid_size(self) -> float:
        """获取对齐网格大小"""
        return self.get("snap_grid_size", 1.0)
    
    def set_snap_grid_size(self, size: float):
        """设置对齐网格大小"""
        self.set("snap_grid_size", size)

    def get_auto_update(self) -> bool:
        """获取自动更新是否启用"""
        return self.get("auto_update", False)

    def set_auto_update(self, enabled: bool):
        """设置自动更新是否启用"""
        self.set("auto_update", enabled)
    
    # 默认参数相关方法
    def get_default_side_angle(self) -> float:
        """获取默认侧面斜角"""
        return self.get("default_side_angle", 0.0)
    
    def set_default_side_angle(self, angle: float):
        """设置默认侧面斜角"""
        self.set("default_side_angle", angle)
    
    def get_default_edge_profile_mode(self) -> str:
        """获取默认边缘形状类型"""
        return self.get("default_edge_profile_mode", "fillet")

    def set_default_edge_profile_mode(self, mode: str):
        """设置默认边缘形状类型"""
        self.set("default_edge_profile_mode", mode)

    def get_default_edge_profile_radius(self) -> float:
        """获取默认边缘半径"""
        return self.get("default_edge_profile_radius", 0.0)

    def set_default_edge_profile_radius(self, radius: float):
        """设置默认边缘半径"""
        self.set("default_edge_profile_radius", radius)

    def get_default_edge_profile_outer(self) -> bool:
        """获取默认外侧边缘是否生效"""
        return self.get("default_edge_profile_outer", True)

    def set_default_edge_profile_outer(self, enabled: bool):
        """设置默认外侧边缘是否生效"""
        self.set("default_edge_profile_outer", enabled)

    def get_default_edge_profile_inner(self) -> bool:
        """获取默认内侧边缘是否生效"""
        return self.get("default_edge_profile_inner", False)

    def set_default_edge_profile_inner(self, enabled: bool):
        """设置默认内侧边缘是否生效"""
        self.set("default_edge_profile_inner", enabled)

    def get_default_edge_profile_left(self) -> bool:
        """获取默认左边是否生效"""
        return self.get("default_edge_profile_left", True)

    def set_default_edge_profile_left(self, enabled: bool):
        """设置默认左边是否生效"""
        self.set("default_edge_profile_left", enabled)

    def get_default_edge_profile_right(self) -> bool:
        """获取默认右边是否生效"""
        return self.get("default_edge_profile_right", True)

    def set_default_edge_profile_right(self, enabled: bool):
        """设置默认右边是否生效"""
        self.set("default_edge_profile_right", enabled)

    def get_default_edge_profile_top(self) -> bool:
        """获取默认上边是否生效"""
        return self.get("default_edge_profile_top", True)

    def set_default_edge_profile_top(self, enabled: bool):
        """设置默认上边是否生效"""
        self.set("default_edge_profile_top", enabled)

    def get_default_edge_profile_bottom(self) -> bool:
        """获取默认下边是否生效"""
        return self.get("default_edge_profile_bottom", True)

    def set_default_edge_profile_bottom(self, enabled: bool):
        """设置默认下边是否生效"""
        self.set("default_edge_profile_bottom", enabled)

    def get_side_angle_step(self) -> float:
        return self.get("side_angle_step", 0.5)

    def set_side_angle_step(self, step: float):
        self.set("side_angle_step", step)

    def get_default_wall_thickness(self) -> float:
        return self.get("default_wall_thickness", 1.0)

    def set_default_wall_thickness(self, v: float):
        self.set("default_wall_thickness", v)

    def get_wall_thickness_step(self) -> float:
        return self.get("wall_thickness_step", 0.1)

    def set_wall_thickness_step(self, step: float):
        self.set("wall_thickness_step", step)

    def get_default_stroke_width(self) -> float:
        return self.get("default_stroke_width", 0.0)

    def set_default_stroke_width(self, v: float):
        self.set("default_stroke_width", v)

    def get_stroke_width_step(self) -> float:
        return self.get("stroke_width_step", 0.05)

    def set_stroke_width_step(self, step: float):
        self.set("stroke_width_step", step)

    def get_edge_radius_step(self) -> float:
        return self.get("edge_radius_step", 0.05)

    def set_edge_radius_step(self, step: float):
        self.set("edge_radius_step", step)

    def get_default_text_height(self) -> float:
        return self.get("default_text_height", 3.0)

    def set_default_text_height(self, v: float):
        self.set("default_text_height", v)

    def get_text_height_step(self) -> float:
        return self.get("text_height_step", 0.1)

    def set_text_height_step(self, step: float):
        self.set("text_height_step", step)

    def get_default_text_depth(self) -> float:
        return self.get("default_text_depth", 0.5)

    def set_default_text_depth(self, v: float):
        self.set("default_text_depth", v)

    def get_text_depth_step(self) -> float:
        return self.get("text_depth_step", 0.05)

    def set_text_depth_step(self, step: float):
        self.set("text_depth_step", step)

    def get_default_stem_cross_width(self) -> float:
        return self.get("default_stem_cross_width", 1.3)

    def set_default_stem_cross_width(self, v: float):
        self.set("default_stem_cross_width", v)

    def get_default_stem_cross_length(self) -> float:
        return self.get("default_stem_cross_length", 4.0)

    def set_default_stem_cross_length(self, v: float):
        self.set("default_stem_cross_length", v)

    def get_default_stem_height(self) -> float:
        return self.get("default_stem_height", 4.0)

    def set_default_stem_height(self, v: float):
        self.set("default_stem_height", v)

    def get_default_stem_cylinder_diameter(self) -> float:
        return self.get("default_stem_cylinder_diameter", 5.4)

    def set_default_stem_cylinder_diameter(self, v: float):
        self.set("default_stem_cylinder_diameter", v)

    def get_default_stem_enabled(self) -> bool:
        return self.get("default_stem_enabled", True)

    def set_default_stem_enabled(self, v: bool):
        self.set("default_stem_enabled", v)

    def get_default_top_thickness(self) -> float:
        return self.get("default_top_thickness", 1.0)

    def set_default_top_thickness(self, v: float):
        self.set("default_top_thickness", v)

    def get_default_stem_type(self) -> str:
        return self.get("default_stem_type", "MX")

    def set_default_stem_type(self, v: str):
        self.set("default_stem_type", v)

    def get_default_corner_radius(self) -> float:
        return self.get("default_corner_radius", 0.5)

    def set_default_corner_radius(self, v: float):
        self.set("default_corner_radius", v)

    def get_default_curved_top_enabled(self) -> bool:
        return self.get("default_curved_top_enabled", False)

    def set_default_curved_top_enabled(self, v: bool):
        self.set("default_curved_top_enabled", v)

    def get_default_curved_top_x_enabled(self) -> bool:
        return self.get("default_curved_top_x_enabled", False)

    def set_default_curved_top_x_enabled(self, v: bool):
        self.set("default_curved_top_x_enabled", v)

    def get_default_curved_top_y_enabled(self) -> bool:
        return self.get("default_curved_top_y_enabled", False)

    def set_default_curved_top_y_enabled(self, v: bool):
        self.set("default_curved_top_y_enabled", v)

    def get_default_curved_top_x_radius(self) -> float:
        return self.get("default_curved_top_x_radius", 90.0)

    def set_default_curved_top_x_radius(self, v: float):
        self.set("default_curved_top_x_radius", v)

    def get_default_curved_top_y_radius(self) -> float:
        return self.get("default_curved_top_y_radius", 90.0)

    def set_default_curved_top_y_radius(self, v: float):
        self.set("default_curved_top_y_radius", v)

    def get_default_curved_top_direction(self) -> str:
        return self.get("default_curved_top_direction", "convex")

    def set_default_curved_top_direction(self, v: str):
        self.set("default_curved_top_direction", v)

    def get_default_stabilizer_enabled(self) -> bool:
        return self.get("default_stabilizer_enabled", False)

    def set_default_stabilizer_enabled(self, v: bool):
        self.set("default_stabilizer_enabled", v)

    def get_default_stabilizer_length(self) -> float:
        return self.get("default_stabilizer_length", 50.0)

    def set_default_stabilizer_length(self, v: float):
        self.set("default_stabilizer_length", v)

    def get_default_stabilizer_cross_width(self) -> float:
        return self.get("default_stabilizer_cross_width", 1.3)

    def set_default_stabilizer_cross_width(self, v: float):
        self.set("default_stabilizer_cross_width", v)

    def get_default_stabilizer_cross_length(self) -> float:
        return self.get("default_stabilizer_cross_length", 4.0)

    def set_default_stabilizer_cross_length(self, v: float):
        self.set("default_stabilizer_cross_length", v)

    def get_default_stabilizer_cylinder_diameter(self) -> float:
        return self.get("default_stabilizer_cylinder_diameter", 4.0)

    def set_default_stabilizer_cylinder_diameter(self, v: float):
        self.set("default_stabilizer_cylinder_diameter", v)

    def get_default_stabilizer_depth(self) -> float:
        return self.get("default_stabilizer_depth", 5.0)

    def set_default_stabilizer_depth(self, v: float):
        self.set("default_stabilizer_depth", v)
    
    # 旧圆角默认参数已移除（改为边缘形状设置）
    
    def get_default_font_path(self) -> str:
        """获取默认字体路径"""
        return self.get("default_font_path", None)
    
    def set_default_font_path(self, font_path: str):
        """设置默认字体路径"""
        self.set("default_font_path", font_path)

    def get_language(self) -> str:
        """界面语言：zh / en"""
        return self.get("language", "zh")

    def set_language(self, lang: str):
        """设置界面语言"""
        self.set("language", lang)
