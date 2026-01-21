"""
按键类型树状列表组件
显示按键类型分组（按长度和字符位置）
"""
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, List


class KeyTypeTreeWidget(QTreeWidget):
    """按键类型树状列表"""
    
    # 信号：选中类型
    type_selected = pyqtSignal(str)  # 类型标识
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("按键类型")
        self.setRootIsDecorated(True)
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)
        
        # 连接选择事件
        self.itemClicked.connect(self._on_item_clicked)
    
    def load_key_types(self, type_map: Dict[str, List[int]]):
        """
        加载按键类型
        
        参数:
            type_map: {类型标识: [按键索引列表]}
        """
        # 清空现有内容
        self.clear()
        
        if not type_map:
            return
        
        # 按长度分组
        length_groups: Dict[float, List[tuple]] = {}
        for type_id, indices in type_map.items():
            # 解析宽度（例如 "1u_9" -> 1.0）
            try:
                width_str = type_id.split('u_')[0]
                width = float(width_str)
            except (ValueError, IndexError):
                width = 1.0  # 默认值
            
            if width not in length_groups:
                length_groups[width] = []
            length_groups[width].append((type_id, indices))
        
        # 构建树
        for width in sorted(length_groups.keys()):
            # 第一级：长度
            length_item = QTreeWidgetItem(self, [f"{width}u"])
            length_item.setExpanded(True)
            
            # 第二级：字符位置组合
            for type_id, indices in sorted(length_groups[width], key=lambda x: x[0]):
                # 提取位置字符串（例如 "1u_0-9" -> "0-9"）
                try:
                    pos_str = type_id.split('u_', 1)[1]
                except IndexError:
                    pos_str = type_id
                
                # 格式化显示文本
                count = len(indices)
                display_text = f"{width}u_{pos_str} ({count}个)"
                
                type_item = QTreeWidgetItem(length_item, [display_text])
                type_item.setData(0, Qt.UserRole, type_id)  # 存储类型标识
                type_item.setToolTip(0, f"类型: {type_id}\n包含 {count} 个按键")
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """处理项目点击"""
        # 获取存储的类型标识
        type_id = item.data(0, Qt.UserRole)
        if type_id:
            self.type_selected.emit(type_id)
