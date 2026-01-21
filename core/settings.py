"""
设置管理
保存和加载软件设置
"""
import json
import os
from pathlib import Path
from typing import Any, Dict


class Settings:
    """设置管理类"""
    
    def __init__(self, config_file: str = "config.json"):
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
                "default_edge_profile_mode": "fillet",
                "default_edge_profile_radius": 0.0,
                "default_edge_profile_outer": True,
                "default_edge_profile_inner": False,
                "default_edge_profile_left": True,
                "default_edge_profile_right": True,
                "default_edge_profile_top": True,
                "default_edge_profile_bottom": True,
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
    
    # 旧圆角默认参数已移除（改为边缘形状设置）
    
    def get_default_font_path(self) -> str:
        """获取默认字体路径"""
        return self.get("default_font_path", None)
    
    def set_default_font_path(self, font_path: str):
        """设置默认字体路径"""
        self.set("default_font_path", font_path)
