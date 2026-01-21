"""
按键类型分析器
分析 KLE 按键列表，提取按键类型并分组
"""
from dataclasses import dataclass
from typing import Dict, List, Set
from core.kle_parser import KLEKey


@dataclass
class KeyTypeSignature:
    """按键类型签名"""
    width: float  # u单位
    height: float  # u单位
    label_positions: Set[int]  # 有字符的位置索引集合 (0-11)
    
    def to_string(self) -> str:
        """
        转换为字符串标识，如 '1u_0-1-9'
        
        返回:
            类型标识字符串
        """
        if not self.label_positions:
            pos_str = "empty"
        else:
            pos_str = '-'.join(sorted(str(p) for p in self.label_positions))
        return f"{self.width}u_{pos_str}"
    
    def __hash__(self):
        """使 KeyTypeSignature 可哈希（用于字典键）"""
        return hash((self.width, self.height, tuple(sorted(self.label_positions))))
    
    def __eq__(self, other):
        """比较两个签名是否相等"""
        if not isinstance(other, KeyTypeSignature):
            return False
        return (self.width == other.width and 
                self.height == other.height and
                self.label_positions == other.label_positions)


class KeyTypeAnalyzer:
    """分析KLE按键列表，提取按键类型"""
    
    @staticmethod
    def analyze_keys(keys: List[KLEKey]) -> Dict[str, List[int]]:
        """
        分析按键类型
        
        参数:
            keys: KLE 按键列表
        
        返回:
            {类型标识: [按键索引列表]}
            例如: {'1u_9': [0, 1, 2, ...], '1u_0-9': [12, 13, ...]}
        """
        type_map: Dict[str, List[int]] = {}
        
        for i, key in enumerate(keys):
            # 提取有字符的位置
            label_positions = {j for j, label in enumerate(key.labels) 
                             if label and label.strip()}
            
            # 创建类型签名
            signature = KeyTypeSignature(
                width=key.width,
                height=key.height,
                label_positions=label_positions
            )
            
            # 转换为字符串标识
            type_id = signature.to_string()
            
            # 添加到映射
            if type_id not in type_map:
                type_map[type_id] = []
            type_map[type_id].append(i)
        
        return type_map
    
    @staticmethod
    def get_signature_for_key(key: KLEKey) -> KeyTypeSignature:
        """
        获取单个按键的类型签名
        
        参数:
            key: KLE 按键
        
        返回:
            KeyTypeSignature 对象
        """
        label_positions = {j for j, label in enumerate(key.labels) 
                          if label and label.strip()}
        
        return KeyTypeSignature(
            width=key.width,
            height=key.height,
            label_positions=label_positions
        )
