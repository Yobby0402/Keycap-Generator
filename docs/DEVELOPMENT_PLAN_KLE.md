# 开发方案：基于 KLE 的多按键批量生成功能

## 1. 目标
通过集成 [Keyboard Layout Editor (KLE)](http://www.keyboard-layout-editor.com/) 的数据格式，实现从键盘布局到 3D 模型的高度自动化批量生成。允许用户导入 KLE JSON 数据，应用统一的键帽几何参数和可配置的字符样式，最终生成全套键帽模型。

## 2. 核心数据结构重构 (Refactoring)

为了支持“几何参数复用”和“字符样式映射”，需要将现有的扁平化 `KeycapParameters` 拆解。

### 2.1 新参数类设计
位于 `core/parameters.py`：

1.  **`KeycapGeometry` (键帽几何参数)**
    *   负责：物理形状、尺寸、轴体。
    *   字段：`profile` (Cherry/OEM), `row` (R1-R4), `width_u`, `height_u`, `wall_thickness`, `stem_type` 等。
    *   *说明*：批量生成时，这通常是全局统一的（或按 Row 自动匹配）。

2.  **`LegendStyle` (字符样式)**
    *   负责：单个字符的视觉表现。
    *   字段：`font_path`, `size` (mm), `offset_x`, `offset_y`, `depth` (凹/凸), `rotation`。

3.  **`LegendMap` (图例映射配置)**
    *   负责：定义 KLE 的 12 个位置索引（0=左上, 4=居中等）如何映射到具体的 `LegendStyle`。
    *   字段：`mapping: Dict[int, LegendStyle]`。
    *   *示例*：`{0: Style(size=3, align=top_left), 4: Style(size=5, align=center)}`。

4.  **`KeyInstance` (按键实例)**
    *   负责：描述具体的某一个按键。
    *   字段：`labels` (文字列表), `u_width`, `u_height`, `x`, `y`, `rotation` (位置信息), `geometry_override` (可选的特定几何覆盖)。

## 3. KLE 集成模块 (KLE Integration)

新建 `core/kle_parser.py`：

*   **功能**：解析 KLE 的 Raw JSON 数据。
*   **逻辑**：
    *   解析 JSON 数组。
    *   处理 KLE 的状态机（KLE 的 JSON 是差异存储的，需要根据前一个按键的状态计算当前按键）。
    *   转换坐标系统（KLE 的 Y 轴向下，原点在左上；需要映射到 3D 场景坐标）。
    *   提取 `labels` 并根据 `LegendMap` 转换为具体的字符参数。

## 4. UI 改造 (UI Implementation)

### 4.1 主窗口重构 (`MainWindow`)
*   引入 `QTabWidget` 或侧边栏切换模式：
    *   **Tab 1: 单键设计 (Single Key)** - 保持现有功能，适配新参数类。
    *   **Tab 2: 批量布局 (Batch Layout)** - 新增功能区。

### 4.2 批量布局界面
*   **左侧面板**：
    *   **布局导入区**：文本框输入 KLE JSON，或“粘贴”按钮。
    *   **全局几何设置**：引用单键模式的设置，或独立设置（如选择高度预设）。
    *   **样式映射配置**：简单的界面，让用户定义“左上角文字多大”、“中间文字多大”。
*   **右侧预览区**：
    *   **2D 布局预览 (`KLEPreviewWidget`)**：
        *   绘制整个键盘布局。
        *   显示按键轮廓和文字。
        *   支持选中按键，在侧边栏微调其特定属性。
    *   **3D 预览**：
        *   可选：生成全部预览（较慢）。
        *   默认：点击 2D 预览中的某个键，仅预览该键的 3D 效果。

## 5. 生成与导出逻辑

*   **批量生成器 (`BatchGenerator`)**：
    *   输入：`KLEData`, `GlobalGeometry`, `LegendMap`。
    *   过程：遍历所有 `KeyInstance`，实例化 `KeycapModeler` 并生成模型。
*   **导出管理器**：
    *   支持“合并导出”（全键盘摆盘）。
    *   支持“按行/列命名导出”（如 `R1_Esc.stl`, `R3_Enter.stl`）。

## 6. 开发步骤规划

### Phase 1: 核心重构与解析器 (Foundation)
1.  **重构 `parameters.py`**：拆分几何与字符参数。
2.  **实现 `kle_parser.py`**：完成 JSON 到 `KeyInstance` 列表的转换逻辑。
3.  **单元测试**：验证解析器对标准 ANSI 104 布局的解析正确性。

### Phase 2: UI 框架与预览 (Preview)
4.  **改造 `MainWindow`**：添加 Tab 结构。
5.  **开发 `KLEPreviewWidget`**：实现基于 QPainter 的 2D 布局绘制。
6.  **集成数据流**：实现从 JSON 输入到 2D 预览的完整链路。

### Phase 3: 样式配置与 3D 生成 (Generation)
7.  **实现样式映射 UI**：让用户控制不同位置字符的大小/字体。
8.  **连接 3D 生成器**：实现点击 2D 按键生成对应 3D 模型的功能。
9.  **批量导出功能**：实现多文件导出逻辑。

### Phase 4: 优化与完善 (Polish)
10. **交互优化**：支持 2D 视图的缩放/平移。
11. **预设管理**：保存/加载用户的样式映射配置。

---
*文档生成日期: 2026-01-21*
