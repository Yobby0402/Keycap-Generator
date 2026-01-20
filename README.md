# 机械键盘按键模型生成器

一个参数化的机械键盘按键（键帽）3D模型生成器，支持自定义字体、字母、按键尺寸和斜角等参数，生成分离的按键本体和文字模型，便于多色3D打印。

## ✨ 功能特性

### 核心功能
- 🎨 **自定义字体和字母** - 支持系统字体和自定义字体文件
- 📐 **参数化按键尺寸** - 宽度、高度、深度完全可调
- 🔺 **可调节斜角** - 顶部、侧面斜角独立控制
- 🔤 **多字符支持** - 可添加多个文字，独立调整位置和大小
- 👁️ **实时预览** - 2D/3D 双预览，所见即所得
- 🔧 **多种轴体** - 支持 MX、Alps 等轴体类型

### 多色打印支持 (v0.2 新增)
- 🎯 **3MF 格式导出** - 单文件包含多部件，完美支持多色打印
- 📦 **智能分离** - 按键主体和文字自动分离为独立对象
- 🌈 **颜色预设** - 自动设置默认颜色（按键=深灰，文字=白色）
- 💾 **多格式支持** - STL、STEP、3MF 三种格式任选

### 智能辅助
- ⚡ **自动更新** - 可选的实时模型更新（带防抖）
- 📍 **快速对齐** - 九宫格预设位置一键对齐
- 🎯 **网格吸附** - 精确定位，可调节吸附网格大小
- 💬 **操作指引** - 详细的导出提示和使用说明

## 🛠️ 技术栈

- **GUI**: PyQt5
- **3D建模**: CadQuery
- **3D预览**: VTK
- **字体处理**: fontTools + shapely
- **3MF导出**: trimesh (可选)

## 📦 安装依赖

### 基础依赖
```bash
pip install -r requirements.txt
```

### 可选依赖（3MF 导出）
```bash
pip install trimesh
```

## 🚀 运行

```bash
python main.py
```

## 📖 使用说明

### 基础流程
1. 选择字体和输入字母
2. 在 2D 预览中调整文字位置（可添加多个）
3. 设置按键尺寸参数（宽度、高度、深度）
4. 调整斜角和文字参数
5. 点击"生成模型"预览
6. 导出文件

### 多色打印推荐流程
1. 生成模型后，使用 `Ctrl+M` 导出 3MF 文件
2. 将 `.3mf` 文件拖入切片软件（Bambu Studio / PrusaSlicer / Cura）
3. 分别为"Keycap"和"Text"部件指定不同颜色/材料
4. 切片并打印

详细说明请参考 [3MF导出说明](docs/3MF导出说明.md)

## 📁 项目结构

```
Keycap-Generator/
├── main.py                 # 程序入口
├── ui/                     # UI界面模块
│   ├── main_window.py      # 主窗口
│   ├── parameter_panel.py  # 参数面板
│   ├── preview_widget.py   # 3D预览
│   └── preview_2d_widget.py # 2D预览
├── core/                   # 核心业务逻辑
│   ├── keycap_modeler.py   # 模型生成器
│   ├── parameters.py       # 参数定义
│   └── settings.py         # 设置管理
├── geometry/               # 几何计算模块
│   ├── keycap_shape.py     # 键帽形状
│   └── text_extrusion.py   # 文字挤出
├── export/                 # 导出模块
│   ├── stl_exporter.py     # STL导出
│   ├── step_exporter.py    # STEP导出
│   └── threemf_exporter.py # 3MF导出 (v0.2)
├── utils/                  # 工具函数
└── docs/                   # 文档
```

## 📝 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细更新内容。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

