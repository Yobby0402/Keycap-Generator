# 批量编辑功能实现文档

## 需求概述

### 1. 界面布局优化
- **导入KLE功能移至菜单栏**：将"导入 KLE 布局数据"按钮从批量布局面板移至菜单栏
- **多按键界面右侧属性面板**：点击按键时，在右侧显示该按键的属性信息
- **三界面堆叠结构**：单键设计、批量布局、批量编辑三个界面通过Tab或按钮切换

### 2. 数据导出功能
- **导出单个按键数据**：支持导出单个按键的配置（几何参数+字符参数）
- **导出一整套按键数据**：支持导出整个键盘布局的所有按键配置

### 3. 批量编辑功能（核心新功能）
- **按键类型分组**：在单键设计界面添加树状列表，按以下规则分组：
  - 第一级：按键长度（1u, 1.25u, 1.5u, 2u等）
  - 第二级：字符位置组合（如 `1u_0-1` 表示1u按键，在位置0和1有字符）
- **分组预览**：点击分组后，右侧显示2D和3D预览，所有字符用"X"代替
- **批量编辑属性**：可编辑该类型按键的字符大小、深度、位置偏移等
- **同步到多按键区域**：保存后，所有该类型的按键自动应用新属性

### 4. 功能保留
- **保留个性化编辑**：原有的单键设计功能保留，用于生成个性化键帽
- **保留双击编辑**：多按键界面双击按键仍可编辑单个按键

## 技术实现方案

### 1. 界面结构重构

#### 1.1 主窗口布局
```
MainWindow
├── MenuBar
│   ├── 文件菜单
│   │   ├── 导入 KLE 布局数据...
│   │   ├── 导出单个按键配置...
│   │   ├── 导出整套按键配置...
│   │   └── 导入按键配置...
│   └── ...
├── TabWidget (三界面切换)
│   ├── Tab 0: 单键设计
│   ├── Tab 1: 批量布局
│   └── Tab 2: 批量编辑
└── StatusBar
```

#### 1.2 单键设计界面（Tab 0）
```
单键设计界面
├── 左侧：参数面板 (ParameterPanel)
└── 右侧：预览区域
    ├── 2D预览 (Preview2DWidget)
    └── 3D预览 (PreviewWidget)
```

#### 1.3 批量布局界面（Tab 1）
```
批量布局界面
├── 上方：预览区域
│   ├── 2D KLE预览 (KLEPreviewWidget)
│   └── 3D预览 (PreviewWidget)
├── 中间：右侧属性面板 (KeyPropertyPanel) - 新增
│   └── 显示选中按键的属性
└── 下方：操作面板 (BatchPanel)
    ├── 样式映射配置
    └── 操作按钮
```

#### 1.4 批量编辑界面（Tab 2）- 新增
```
批量编辑界面
├── 左侧：按键类型树 (KeyTypeTreeWidget)
│   └── 树状列表，按长度和字符位置分组
├── 中间：编辑区域
│   ├── 参数面板 (批量编辑专用)
│   └── 预览区域
│       ├── 2D预览（字符用X代替）
│       └── 3D预览（字符用X代替）
└── 右侧：应用范围预览 (可选)
    └── 显示该类型按键在KLE布局中的分布
```

### 2. 数据结构设计

#### 2.1 按键类型标识
```python
@dataclass
class KeyTypeSignature:
    """按键类型签名"""
    width: float  # u单位
    height: float  # u单位
    label_positions: set[int]  # 有字符的位置索引集合 (0-11)
    
    def to_string(self) -> str:
        """转换为字符串标识，如 '1u_0-1-9'"""
        pos_str = '-'.join(sorted(str(p) for p in self.label_positions))
        return f"{self.width}u_{pos_str}"
```

#### 2.2 按键配置数据
```python
@dataclass
class KeycapConfig:
    """按键配置（可导出/导入）"""
    geometry: KeycapGeometry
    text_items: List[TextParameters]
    key_type: KeyTypeSignature  # 类型标识
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KeycapConfig':
        """从字典反序列化"""
        ...
```

#### 2.3 批量编辑配置
```python
@dataclass
class BatchEditConfig:
    """批量编辑配置"""
    key_type: KeyTypeSignature
    geometry: KeycapGeometry  # 几何参数（所有该类型按键共用）
    text_styles: Dict[int, LegendStyle]  # 位置索引 -> 样式
    # 例如：{0: LegendStyle(size=3.0, ...), 9: LegendStyle(size=5.0, ...)}
```

### 3. 核心功能实现

#### 3.1 按键类型分析器
```python
class KeyTypeAnalyzer:
    """分析KLE按键列表，提取按键类型"""
    
    @staticmethod
    def analyze_keys(keys: List[KLEKey]) -> Dict[str, List[int]]:
        """
        分析按键类型
        
        返回:
            {类型标识: [按键索引列表]}
        """
        type_map = {}
        for i, key in enumerate(keys):
            # 提取有字符的位置
            label_positions = {j for j, label in enumerate(key.labels) if label and label.strip()}
            signature = KeyTypeSignature(key.width, key.height, label_positions)
            type_id = signature.to_string()
            
            if type_id not in type_map:
                type_map[type_id] = []
            type_map[type_id].append(i)
        
        return type_map
```

#### 3.2 树状列表组件
```python
class KeyTypeTreeWidget(QTreeWidget):
    """按键类型树状列表"""
    
    # 信号
    type_selected = pyqtSignal(str)  # 类型标识
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("按键类型")
        self.setRootIsDecorated(True)
        
    def load_key_types(self, type_map: Dict[str, List[int]]):
        """加载按键类型"""
        # 按长度分组
        length_groups = {}
        for type_id, indices in type_map.items():
            width = float(type_id.split('u_')[0])
            if width not in length_groups:
                length_groups[width] = []
            length_groups[width].append((type_id, indices))
        
        # 构建树
        for width in sorted(length_groups.keys()):
            length_item = QTreeWidgetItem(self, [f"{width}u"])
            for type_id, indices in sorted(length_groups[width]):
                pos_str = type_id.split('u_')[1]
                type_item = QTreeWidgetItem(length_item, [f"{width}u_{pos_str} ({len(indices)}个)"])
                type_item.setData(0, Qt.UserRole, type_id)
```

#### 3.3 批量编辑参数面板
```python
class BatchEditPanel(QWidget):
    """批量编辑参数面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_type: Optional[KeyTypeSignature] = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 类型信息
        self.type_label = QLabel("未选择类型")
        layout.addWidget(self.type_label)
        
        # 几何参数（共用）
        geometry_group = QGroupBox("几何参数（所有该类型按键共用）")
        # ... 几何参数控件
        layout.addWidget(geometry_group)
        
        # 字符样式（按位置）
        style_group = QGroupBox("字符样式")
        self.style_widgets = {}  # {位置索引: 样式控件组}
        # ... 为每个位置创建样式编辑控件
        layout.addWidget(style_group)
        
        # 保存按钮
        save_btn = QPushButton("保存并应用到所有该类型按键")
        save_btn.clicked.connect(self.save_and_apply)
        layout.addWidget(save_btn)
    
    def load_type(self, key_type: KeyTypeSignature, config: BatchEditConfig):
        """加载类型配置"""
        self.current_type = key_type
        self.type_label.setText(f"类型: {key_type.to_string()}")
        # 加载配置到控件
        ...
    
    def save_and_apply(self):
        """保存并应用到所有该类型按键"""
        # 收集配置
        config = self.collect_config()
        # 发出信号
        self.config_saved.emit(config)
```

#### 3.4 批量编辑预览（字符用X代替）
```python
class BatchEditPreview2D(Preview2DWidget):
    """批量编辑2D预览（字符用X代替）"""
    
    def update_preview(self, key_type: KeyTypeSignature, config: BatchEditConfig):
        """更新预览"""
        # 创建临时KeycapDesign，所有字符用"X"
        geometry = config.geometry
        text_items = []
        for pos_idx in key_type.label_positions:
            style = config.text_styles.get(pos_idx, LegendStyle())
            # 使用X代替实际字符
            text_param = TextParameters(
                text="X",
                font_path=style.font_path,
                size=style.size,
                depth=style.depth,
                offset_x=...,  # 根据位置计算
                offset_y=...
            )
            text_items.append(text_param)
        
        design = KeycapDesign(geometry=geometry, text_items=text_items)
        # 更新预览
        ...
```

### 4. 数据流设计

#### 4.1 导入KLE数据流
```
菜单栏"导入KLE" 
  → KLEImportDialog 
    → KLEParser.parse() 
      → MainWindow.on_kle_imported(keys)
        → 更新批量布局界面
        → 分析按键类型
        → 更新批量编辑界面的树状列表
```

#### 4.2 批量编辑数据流
```
批量编辑界面
  → 选择类型 
    → 加载该类型的当前配置
    → 显示在参数面板和预览
  → 编辑参数
    → 实时更新预览（字符用X）
  → 点击保存
    → 收集配置
    → 应用到所有该类型按键
    → 更新批量布局界面的2D预览
```

#### 4.3 导出数据流
```
菜单栏"导出整套配置"
  → 收集所有按键类型
  → 为每个类型创建KeycapConfig
  → 序列化为JSON
  → 保存到文件

菜单栏"导出单个按键配置"
  → 获取当前选中的按键（批量布局或批量编辑）
  → 创建KeycapConfig
  → 序列化为JSON
  → 保存到文件
```

### 5. 文件结构

#### 5.1 新增文件
```
core/
  ├── key_type_analyzer.py      # 按键类型分析器
  ├── keycap_config.py          # 按键配置数据类（导出/导入）
  └── batch_edit_config.py      # 批量编辑配置

ui/
  ├── key_type_tree_widget.py   # 按键类型树状列表
  ├── batch_edit_panel.py       # 批量编辑参数面板
  ├── batch_edit_preview_2d.py # 批量编辑2D预览（X代替字符）
  ├── key_property_panel.py     # 按键属性面板（批量布局右侧）
  └── batch_edit_tab.py         # 批量编辑Tab界面
```

#### 5.2 修改文件
```
ui/main_window.py
  - 添加菜单栏"导入KLE"
  - 添加Tab 2: 批量编辑
  - 添加导出功能

ui/batch_panel.py
  - 移除"导入KLE"按钮
  - 添加右侧属性面板引用

core/batch_generator.py
  - 支持从BatchEditConfig生成按键
```

### 6. 实现步骤

#### Phase 1: 基础重构
1. 将导入KLE移至菜单栏
2. 在批量布局界面添加右侧属性面板
3. 修复单个按键生成无字符的问题

#### Phase 2: 数据结构
4. 实现KeyTypeSignature和KeyTypeAnalyzer
5. 实现KeycapConfig（导出/导入）
6. 实现BatchEditConfig

#### Phase 3: 批量编辑界面
7. 创建KeyTypeTreeWidget
8. 创建BatchEditPanel
9. 创建BatchEditPreview2D（X代替字符）
10. 创建BatchEditTab并集成到主窗口

#### Phase 4: 数据同步
11. 实现批量编辑配置应用到KLE按键
12. 实现导出/导入功能
13. 测试完整流程

### 7. 注意事项

1. **字符位置映射**：确保KLE的12位置索引与批量编辑的位置索引一致
2. **配置兼容性**：导出/导入的配置格式要考虑向后兼容
3. **性能优化**：批量应用配置时，避免逐个重新生成模型，可以批量更新
4. **用户体验**：
   - 批量编辑保存时显示进度
   - 提供"撤销"功能（可选）
   - 树状列表支持搜索/过滤

### 8. 示例：按键类型分组

假设KLE布局包含以下按键：
- 1u按键，位置9有字符"Q" → `1u_9`
- 1u按键，位置0和9有字符"~"和"`" → `1u_0-9`
- 1.5u按键，位置9有字符"Tab" → `1.5u_9`
- 2u按键，位置9有字符"Backspace" → `2u_9`

树状列表显示：
```
1u
  ├── 1u_9 (10个)
  └── 1u_0-9 (12个)
1.5u
  └── 1.5u_9 (1个)
2u
  └── 2u_9 (1个)
```

点击`1u_9`后：
- 右侧显示1u按键的2D/3D预览，字符用"X"代替
- 参数面板显示位置9的字符样式（大小、深度、位置等）
- 编辑后保存，所有10个`1u_9`类型的按键都会应用新样式

---

*文档生成日期: 2026-01-21*
