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
