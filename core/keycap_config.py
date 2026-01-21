"""
按键配置数据类
用于导出/导入单个按键或整套按键的配置
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
from core.parameters import KeycapGeometry, TextParameters, KeycapDesign
from core.key_type_analyzer import KeyTypeSignature
from core.kle_parser import KLEKey


@dataclass
class KeycapConfig:
    """按键配置（可导出/导入）"""
    geometry: KeycapGeometry
    text_items: List[TextParameters]
    key_type: KeyTypeSignature  # 类型标识
    
    def to_dict(self) -> dict:
        """
        序列化为字典
        
        返回:
            字典格式的配置数据
        """
        return {
            "geometry": self._geometry_to_dict(self.geometry),
            "text_items": [self._text_params_to_dict(tp) for tp in self.text_items],
            "key_type": {
                "width": self.key_type.width,
                "height": self.key_type.height,
                "label_positions": list(self.key_type.label_positions)
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KeycapConfig':
        """
        从字典反序列化
        
        参数:
            data: 字典格式的配置数据
        
        返回:
            KeycapConfig 对象
        """
        geometry = cls._geometry_from_dict(data["geometry"])
        text_items = [cls._text_params_from_dict(tp) for tp in data["text_items"]]
        key_type_data = data["key_type"]
        key_type = KeyTypeSignature(
            width=key_type_data["width"],
            height=key_type_data["height"],
            label_positions=set(key_type_data["label_positions"])
        )
        
        return cls(geometry=geometry, text_items=text_items, key_type=key_type)
    
    @staticmethod
    def _geometry_to_dict(geometry: KeycapGeometry) -> dict:
        """将 KeycapGeometry 转换为字典"""
        return asdict(geometry)
    
    @staticmethod
    def _geometry_from_dict(data: dict) -> KeycapGeometry:
        """从字典创建 KeycapGeometry"""
        return KeycapGeometry(**data)
    
    @staticmethod
    def _text_params_to_dict(tp: TextParameters) -> dict:
        """将 TextParameters 转换为字典"""
        return asdict(tp)
    
    @staticmethod
    def _text_params_from_dict(data: dict) -> TextParameters:
        """从字典创建 TextParameters"""
        return TextParameters(**data)
    
    def to_json(self, indent: int = 2) -> str:
        """
        序列化为 JSON 字符串
        
        参数:
            indent: JSON 缩进（默认2）
        
        返回:
            JSON 字符串
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'KeycapConfig':
        """
        从 JSON 字符串反序列化
        
        参数:
            json_str: JSON 字符串
        
        返回:
            KeycapConfig 对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_kle_key(cls, key: KLEKey, design: KeycapDesign) -> 'KeycapConfig':
        """
        从 KLEKey 和 KeycapDesign 创建配置
        
        参数:
            key: KLE 按键数据
            design: 键帽设计对象
        
        返回:
            KeycapConfig 对象
        """
        from core.key_type_analyzer import KeyTypeAnalyzer
        key_type = KeyTypeAnalyzer.get_signature_for_key(key)
        
        return cls(
            geometry=design.geometry,
            text_items=design.text_items,
            key_type=key_type
        )


@dataclass
class KeycapConfigSet:
    """整套按键配置集合"""
    configs: Dict[str, KeycapConfig] = field(default_factory=dict)  # {类型标识: KeycapConfig}
    version: str = "1.0"  # 配置格式版本
    
    def add_config(self, type_id: str, config: KeycapConfig):
        """添加配置"""
        self.configs[type_id] = config
    
    def get_config(self, type_id: str) -> Optional[KeycapConfig]:
        """获取配置"""
        return self.configs.get(type_id)
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "version": self.version,
            "configs": {type_id: config.to_dict() for type_id, config in self.configs.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KeycapConfigSet':
        """从字典反序列化"""
        version = data.get("version", "1.0")
        configs = {
            type_id: KeycapConfig.from_dict(config_data)
            for type_id, config_data in data["configs"].items()
        }
        return cls(configs=configs, version=version)
    
    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'KeycapConfigSet':
        """从 JSON 字符串反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)
