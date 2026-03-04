# 🎹 机械键盘按键模型生成器

> **一个让你从"买不起键盘"到"自己打印键盘"的神器！** 🚀

还在为动辄几百几千的机械键盘而心疼钱包吗？还在各种网购软件里翻来翻去找不到心仪的配列和键帽吗？别慌，这个工具就是来拯救你的！

从 [Keyboard Layout Editor (KLE)](http://www.keyboard-layout-editor.com/) 导入布局，配置几何与字符样式，生成整盘键帽与字符 3D 模型，导出为 STL / STEP / 3MF，在切片软件中按颜色分配耗材即可多色打印。**从此告别"买不起"，拥抱"自己造"！**

**版本：Release V1.0** | [English Version](#english-version) 👇

---

## ✨ 功能特性

### 🎯 单键设计：从零开始打造你的专属键帽

- **自定义字体与字符**：系统字体？本地字体？统统支持！想加几个字就加几个，想放哪就放哪，想多大就多大，甚至还能塞张图片进去（没错，就是这么任性）
- **参数化几何**：宽度、高度、深度、侧面斜角、圆角、边缘类型...想怎么调就怎么调，调到你满意为止
- **2D / 3D 实时预览**：2D 里拖拽字符位置，3D 里看效果，所见即所得，再也不用"打印出来才知道长啥样"

### ⌨️ 键盘设计：整盘布局，一键搞定

- **导入 KLE 布局**：从 [keyboard-layout-editor.com](http://www.keyboard-layout-editor.com/) 复制 Raw data，粘贴即可。支持布局中的 `{c:"#xxx",t:"#xxx"}` 按键/文字颜色，导入后颜色自动保留（懒人福音）
- **2D 预览**：按 KLE 的 x/y 保留数字区与字母区等间隔，支持单击、框选、Ctrl 多选按键编辑颜色（想怎么选就怎么选）
- **按键属性**：单选时编辑字符与颜色；多选时批量设置按键色/文字色；支持「应用已有方案」——从当前布局中已用配色里选一种，以双色块预览，一键应用（配色困难户的救星）
- **3D 预览带颜色**：单键与整盘预览均按按键色/文字色显示，打印前就能看到最终效果

### 🎨 键盘参数：按类型批量配置，效率拉满

- **按键类型树**：按宽高、字符位置等自动归纳类型，可为每种类型单独配置几何、字符样式、按键/文字颜色（再也不用一个个按键慢慢调了）
- **2D / 3D 预览**：在键盘参数页中调整字符位置与样式，支持九宫格对齐（强迫症患者的福音）
- **保存并应用**：将当前类型的配置写回该类型下所有按键（含颜色），再在「键盘设计」中生成即可生效

### 🖨️ 导出与多色打印：让打印机发挥最大价值

- **STL / STEP / 3MF**：支持单键导出与整盘导出；3MF 时按「按键色 + 文字色」分组，同色键帽/文字合并为同一 mesh，便于在切片软件中按耗材批量设置（多色打印的终极解决方案）
- **单键**：菜单或快捷键导出当前单键的键帽+文字
- **整盘**：「导出所有」可选「按按键分文件」或「合并为一个/多个文件」；选 3MF 合并时，同色已合并，直接按对象指定材料即可（切片软件里点几下就搞定）

### ⚙️ 其它：细节决定成败

- **设置**：默认字体、默认线宽/壁厚/斜角/边缘/文字参数及调节步长，单键与键盘参数中的控件会同步这些默认与步长
- **视图**：吸附、网格、默认参数等在菜单与设置中可调

---

## 🛠️ 技术栈

- **GUI**：PyQt5（界面友好，操作流畅）
- **3D 建模**：CadQuery（参数化建模，想怎么改就怎么改）
- **3D 预览**：VTK（实时预览，所见即所得）
- **字体/轮廓**：fontTools、shapely（字体处理，支持各种字体格式）
- **3MF 导出**：trimesh（可选，多色打印必备）

---

## 📦 安装与运行

### 1. 环境要求

- Python 3.8+（别用太老的版本，会哭的）
- 见 `requirements.txt`（依赖都在这里）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

**3MF 导出（推荐多色打印时安装）：**

```bash
pip install trimesh
```

> 💡 **提示**：如果你打算做多色打印，强烈建议安装 trimesh，不然导出 3MF 时会提示你安装（别问我怎么知道的）

### 3. 启动程序

```bash
python main.py
```

> 🎉 **恭喜！** 现在你已经可以开始造键盘了！

---

## 📖 如何使用

### 🚀 快速开始：从零到打印

如果你要从头开始打印一个键盘，那么最合适的方式就是：

1. **打开 [Keyboard Layout Editor](http://www.keyboard-layout-editor.com/)**，创建你想要的布局，随后导入 Raw Data 到本软件。
   - 导入方式：**文件 → 导入 KLE 布局数据 → 粘贴 → 解析并导入**
   - 导入后你应该可以在**键盘设计**页的 2D 预览区域看到预览效果

2. **在 2D 预览中设置按键基础设计**
   - 你可以单个生成选中的单个按键预览 3D 模型
   - 也可以生成所有按键的模型，其中模型间距设置可以使按键的模型隔开一定的间距，便于打印（打印时不会粘在一起）

3. **调整键盘按键的模型参数**
   - 点击**键盘参数**页，你应该可以看到你导入键盘的所有类型的按键
   - 它们会按照宽度和字符的位置进行分组
   - 你可以设置统一某种按键的几何参数（再也不用一个个按键慢慢调了）

4. **处理异常按键**
   - 如果生成的按键有单个出现错误（比如默认的 KLE 布局中的 JD40 右上角的 Backspace 按键）
   - 你可以尝试调整或者干脆忽略这个模型
   - 生成 3MF 之后尝试通过**添加负零件**的方式跳过这个模型
   - 该操作的方式为在 Bambu Studio 或者 Orca 中点击选中模型，右键添加负零件，调整这个零件使其完全覆盖这个坏掉的按键，然后切片就可以看到这个按键被跳过了
   - 随后你可以单独制作一个单键打印

### 📝 详细使用指南

#### 一、单键设计（做一个键）

1. 打开 **「单键设计」** 标签页
2. 在左侧参数里选择字体、输入字符，在 2D 预览中拖拽字符位置，可插入多个文字（想加几个加几个）
3. 设置键帽尺寸、深度、斜角、边缘、文字高度/深度等（调到你满意为止）
4. 点击 **「生成模型」**，在 3D 预览中查看（所见即所得）
5. 通过菜单 **「文件 → 导出」** 或快捷键导出 STL/STEP/3MF

#### 二、键盘设计（整盘从 KLE 到导出）

##### 1. 导入 KLE 布局

1. 打开 [Keyboard Layout Editor](http://www.keyboard-layout-editor.com/)
2. 在网页中设计或打开一个布局，点击 **「Raw data」** 复制 JSON 文本
3. 本软件中：**「文件 → 导入 KLE 布局数据」**（或 `Ctrl+K`），在弹窗中粘贴并解析
4. 解析成功后，**「键盘设计」** 标签页左侧会显示 2D 布局；若 KLE 中使用了 `{c:"#色",t:"#色"}`，导入后会保留按键/文字颜色

##### 2. 在 2D 中选键与改颜色

- **单击**：选中一个键，右侧「按键属性」中可改字符、按键色、文字色；改完后需点 **「生成当前选中」** 才会更新 3D
- **框选 / Ctrl+点击**：多选后右侧仅显示「批量设置颜色」，选好按键色与文字色后点 **「批量设置颜色」** 应用（效率拉满）
- **应用已有方案**：在「应用已有方案」下拉里会列出当前布局里已出现的配色（双色块预览：左=按键色，右=文字色），选一项即对该键或当前多选键应用该配色（配色困难户的救星）

##### 3. 生成 3D 预览

- **生成当前选中**：先单击选中一个键，再点 **「生成当前选中 (预览)」**，下方 3D 区会显示该键的键帽+文字（按该键配色显示）
- **生成所有按键预览**：点 **「生成所有按键预览」**，按当前布局与「键盘参数」中的类型配置生成整盘 3D，并显示颜色。生成后可点 **「取消生成」** 清空 3D 预览

> 💡 **说明**：导入或修改数据时**不会**自动生成 3D，只有点击上述按钮才会生成，方便你先改布局和参数再统一生成（避免卡顿，贴心设计）

##### 4. 整盘导出

- 点击 **「导出所有…」**，选择目录与导出方式：
  - **按按键分文件**：每个键单独一组 STL/STEP 文件（适合单独打印）
  - **合并**：整盘合并为一个（或键帽/文字各一个）文件；若选 **3MF**，同色键帽、同色文字会各并为一个 mesh，便于在切片软件里按对象分配耗材（多色打印的终极解决方案）

##### 5. 键帽高度（深度）的优先级说明

键帽的「高度」在程序里对应**键帽深度**（从键帽顶面到底部的竖直尺寸，单位 mm），有两处可以设置：

| 设置位置 | 含义 |
|----------|------|
| **键盘参数** 页 | 每种按键类型有一个 **「深度」**，作为该类型键帽的默认高度 |
| **键盘设计** 页 | 下方有 **「各行高度设置」** 表格，可按 KLE 的**行（y 坐标）**为每一行单独指定高度；需勾选 **「使用高度类型（覆盖单个按键的高度设置）」** 后才会生效 |

**最终采用规则**：生成预览或导出时，若已勾选「使用高度类型」且当前按键所在行在「各行高度设置」表格中有设置值，则**使用该行的行高度**（键盘设计里的设置）；否则使用**该按键类型在键盘参数里配置的深度**。  
即：**键盘设计中的行高度会覆盖键盘参数中的深度**，便于按行做阶梯高度（如 R1～R4 不同高度）。

#### 三、键盘参数（按类型统一配置）

1. 打开 **「键盘参数」** 标签页
2. 左侧为按键类型树（由当前 KLE 布局按宽高、字符位置等自动归纳）；选中某一类型
3. 中间编辑该类型的几何（深度、斜角、圆角、边缘、卫星轴等）与字符样式（各位置字体、大小、深度）；可为该类型设置**按键颜色**与**文字颜色**
4. 右侧 2D/3D 预览该类型的效果；2D 下可用菜单 **「对齐」** 做九宫格等对齐（强迫症患者的福音）
5. 点 **「保存并应用」**，将该类型的配置（含颜色）写回该类型下所有按键；再回到 **「键盘设计」** 生成/导出即可

#### 四、多色打印建议（3MF）

1. 在「键盘设计」或「键盘参数」中设好各键的按键色/文字色
2. 整盘生成后，用 **「导出所有…」** 选择 **3MF 合并**
3. 将生成的 `.3mf` 导入切片软件（Bambu Studio / PrusaSlicer / Cura 等），**作为同一工程/对象导入**
4. 在切片软件中按「对象」或「部件」为不同颜色的 mesh 指定不同料盘/颜色即可（切片软件里点几下就搞定）

更多细节见 [3MF 导出说明](docs/3MF导出说明.md)。

---

## 📁 项目结构概览

```
Keycap-Generator/
├── main.py                  # 程序入口（从这里开始）
├── requirements.txt         # 依赖列表（安装前先看看）
├── ui/                      # 界面（UI 都在这里）
│   ├── main_window.py       # 主窗口与标签页（单键/键盘设计/键盘参数）
│   ├── parameter_panel.py   # 单键参数（调参数的地方）
│   ├── batch_panel.py       # 键盘设计：间距、高度、生成/导出按钮
│   ├── batch_edit_tab.py    # 键盘参数：类型树、配置、2D/3D 预览
│   ├── kle_preview_widget.py# KLE 2D 预览与框选（选键的地方）
│   ├── key_property_panel.py# 按键属性与颜色、应用已有方案
│   ├── preview_widget.py    # 3D 预览（VTK，看效果的地方）
│   └── ...                  # 其他 UI 组件
├── core/                    # 核心（核心逻辑都在这里）
│   ├── kle_parser.py        # KLE JSON 解析（含 c/t 颜色）
│   ├── batch_generator.py   # 整盘生成（生成模型的地方）
│   ├── batch_edit_config.py # 类型配置（含颜色）
│   └── ...                  # 其他核心模块
├── export/                  # 导出（导出功能都在这里）
│   ├── stl_exporter.py      # STL 导出
│   ├── step_exporter.py     # STEP 导出
│   └── threemf_exporter.py  # 3MF 导出（含同色合并）
├── docs/                    # 文档（文档都在这里）
│   ├── 3MF导出说明.md       # 3MF 导出详细说明
│   └── KLE_default_layout.md# 内置 KLE 示例
└── ...                      # 其他文件
```

---

## 📝 版本与更新

- **Release V1.0**：单键设计、KLE 整盘导入、键盘参数按类型配置、按键/文字颜色、应用已有方案（双色预览）、3MF 同色合并、生成/取消生成逻辑等

更多历史与细节见 [CHANGELOG.md](CHANGELOG.md)。

---

## 📄 许可证

MIT License（想怎么用就怎么用）

---

## 🤝 参与

欢迎提交 Issue 与 Pull Request（有问题就提，有改进就贡献）！

---

<a name="english-version"></a>
# 🎹 Keycap Model Generator

> **From "can't afford a keyboard" to "printing your own keyboard" - your ultimate solution!** 🚀

Tired of mechanical keyboards costing hundreds or thousands? Can't find the perfect layout and keycaps after browsing countless online stores? Don't worry, this tool is here to save you!

Import layouts from [Keyboard Layout Editor (KLE)](http://www.keyboard-layout-editor.com/), configure geometry and character styles, generate full keyboard keycap and character 3D models, export as STL / STEP / 3MF, and assign materials by color in your slicer for multi-color printing. **Say goodbye to "can't afford" and embrace "DIY"!**

**Version: Release V1.0**

---

## ✨ Features

### 🎯 Single Key Design: Build Your Custom Keycap from Scratch

- **Custom Fonts & Characters**: System fonts? Local fonts? All supported! Add as many characters as you want, place them wherever you like, resize them freely, and even insert custom images (yes, it's that flexible)
- **Parametric Geometry**: Width, height, depth, side angle, corner radius, edge type... adjust everything to your heart's content
- **2D / 3D Real-time Preview**: Drag characters in 2D, preview effects in 3D - what you see is what you get, no more surprises after printing

### ⌨️ Keyboard Design: Full Layout, One-Click Solution

- **Import KLE Layout**: Copy Raw data from [keyboard-layout-editor.com](http://www.keyboard-layout-editor.com/), paste and you're done. Supports `{c:"#xxx",t:"#xxx"}` key/text colors from layouts, colors are automatically preserved (lazy-friendly)
- **2D Preview**: Preserves spacing between numeric and alphanumeric areas according to KLE's x/y coordinates. Supports single-click, drag-select, and Ctrl+click multi-select for color editing (select however you want)
- **Key Properties**: Edit characters and colors for single selection; batch set key/text colors for multi-selection; supports "Apply Existing Scheme" - choose from existing color schemes in the current layout with dual-color preview, one-click apply (savior for color-matching challenged users)
- **3D Preview with Colors**: Both single key and full keyboard previews display with key/text colors, see the final effect before printing

### 🎨 Keyboard Parameters: Batch Configuration by Type, Maximum Efficiency

- **Key Type Tree**: Automatically categorizes by width, height, character positions, etc. Configure geometry, character styles, and key/text colors separately for each type (no more adjusting keys one by one)
- **2D / 3D Preview**: Adjust character positions and styles in the keyboard parameters page, supports 9-grid alignment (perfectionists' dream)
- **Save and Apply**: Write the current type's configuration (including colors) back to all keys of that type, then generate/export in "Keyboard Design"

### 🖨️ Export & Multi-color Printing: Maximize Your Printer's Potential

- **STL / STEP / 3MF**: Supports single key and full keyboard export; 3MF groups by "key color + text color", merges same-color keycaps/text into the same mesh for easy material assignment in slicers (ultimate solution for multi-color printing)
- **Single Key**: Export current key's keycap+text via menu or shortcut
- **Full Keyboard**: "Export All" offers "Separate by key" or "Merge into one/multiple files"; when selecting 3MF merge, same colors are already merged, just assign materials by object (done in a few clicks in your slicer)

### ⚙️ Others: Details Make the Difference

- **Settings**: Default font, default stroke width/wall thickness/angle/edge/text parameters and adjustment steps. Controls in single key and keyboard parameters sync with these defaults and steps
- **View**: Snap, grid, default parameters adjustable in menu and settings

---

## 🛠️ Tech Stack

- **GUI**: PyQt5 (user-friendly interface, smooth operation)
- **3D Modeling**: CadQuery (parametric modeling, modify however you want)
- **3D Preview**: VTK (real-time preview, what you see is what you get)
- **Font/Outline**: fontTools, shapely (font processing, supports various font formats)
- **3MF Export**: trimesh (optional, essential for multi-color printing)

---

## 📦 Installation & Running

### 1. Requirements

- Python 3.8+ (don't use too old versions, it will cry)
- See `requirements.txt` (all dependencies are here)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**3MF Export (recommended for multi-color printing):**

```bash
pip install trimesh
```

> 💡 **Tip**: If you plan to do multi-color printing, strongly recommend installing trimesh, otherwise you'll be prompted to install it when exporting 3MF (don't ask how I know)

### 3. Start the Program

```bash
python main.py
```

> 🎉 **Congratulations!** Now you can start building keyboards!

---

## 📖 How to Use

### 🚀 Quick Start: From Zero to Print

If you want to print a keyboard from scratch, here's the best approach:

1. **Open [Keyboard Layout Editor](http://www.keyboard-layout-editor.com/)** and create your desired layout, then import Raw Data into this software.
   - Import method: **File → Import KLE Layout Data → Paste → Parse and Import**
   - After import, you should see the preview in the 2D preview area of the **Keyboard Design** page

2. **Set basic key design in 2D preview**
   - You can generate a single selected key's 3D model preview
   - Or generate all keys' models, where model spacing settings can separate key models for easier printing (won't stick together when printing)

3. **Adjust keyboard key model parameters**
   - Click the **Keyboard Parameters** page, you should see all key types from your imported keyboard
   - They're grouped by width and character positions
   - You can set unified geometric parameters for a certain type of keys (no more adjusting keys one by one)

4. **Handle abnormal keys**
   - If individual keys have errors (like the Backspace key in the top right of JD40 in default KLE layout)
   - You can try adjusting or simply ignore that model
   - After generating 3MF, try skipping that model using **"Add Negative Part"**
   - In Bambu Studio or Orca, select the model, right-click "Add Negative Part", adjust it to completely cover the broken key, then slice to see the key skipped
   - You can then make a single key print separately

### 📝 Detailed Usage Guide

#### I. Single Key Design (Make One Key)

1. Open the **"Single Key Design"** tab
2. Select font and input characters in left parameters, drag character positions in 2D preview, can insert multiple texts (add as many as you want)
3. Set keycap size, depth, angle, edge, text height/depth, etc. (adjust until satisfied)
4. Click **"Generate Model"**, view in 3D preview (what you see is what you get)
5. Export STL/STEP/3MF via menu **"File → Export"** or shortcut

#### II. Keyboard Design (Full Keyboard from KLE to Export)

##### 1. Import KLE Layout

1. Open [Keyboard Layout Editor](http://www.keyboard-layout-editor.com/)
2. Design or open a layout in the webpage, click **"Raw data"** to copy JSON text
3. In this software: **"File → Import KLE Layout Data"** (or `Ctrl+K`), paste and parse in the popup
4. After successful parsing, the **"Keyboard Design"** tab will show 2D layout on the left; if KLE uses `{c:"#color",t:"#color"}`, key/text colors will be preserved after import

##### 2. Select Keys and Change Colors in 2D

- **Single Click**: Select a key, edit character, key color, text color in right "Key Properties"; need to click **"Generate Current Selection"** to update 3D after changes
- **Drag Select / Ctrl+Click**: After multi-selection, right side only shows "Batch Set Colors", select key color and text color then click **"Batch Set Colors"** to apply (maximum efficiency)
- **Apply Existing Scheme**: The "Apply Existing Scheme" dropdown lists existing color schemes in current layout (dual-color preview: left=key color, right=text color), select one to apply to the key or current multi-selected keys (savior for color-matching challenged users)

##### 3. Generate 3D Preview

- **Generate Current Selection**: First click to select a key, then click **"Generate Current Selection (Preview)"**, 3D area below will show that key's keycap+text (displayed with that key's color scheme)
- **Generate All Keys Preview**: Click **"Generate All Keys Preview"**, generates full keyboard 3D according to current layout and type configurations in "Keyboard Parameters", displays colors. After generation, can click **"Cancel Generation"** to clear 3D preview

> 💡 **Note**: Importing or modifying data does **NOT** automatically generate 3D, only clicking the above buttons will generate, allowing you to modify layout and parameters first then generate uniformly (avoids lag, thoughtful design)

##### 4. Full Keyboard Export

- Click **"Export All…"**, select directory and export method:
  - **Separate by Key**: Each key as separate STL/STEP files (suitable for separate printing)
  - **Merge**: Full keyboard merged into one (or keycap/text each as one) file; if selecting **3MF**, same-color keycaps and same-color text are each merged into one mesh for easy material assignment by object in slicer (ultimate solution for multi-color printing)

##### 5. Keycap Height (Depth) Priority

Keycap "height" in the program is **keycap depth** (vertical size from top to bottom, in mm). It can be set in two places:

| Where | Meaning |
|-------|--------|
| **Keyboard Parameters** tab | Each key type has a **"Depth"** field, used as the default keycap height for that type |
| **Keyboard Design** tab | The **"Row heights"** table lets you set a height per **row** (KLE y coordinate). The option **"Use height profile (override per-key height)"** must be checked for these values to apply |

**Final rule**: When generating preview or exporting, if "Use height profile" is enabled and the current key's row has a value in the row heights table, that **row height** (from Keyboard Design) is used; otherwise the **depth** for that key type (from Keyboard Parameters) is used. So **row heights override per-type depth**, which is useful for row-dependent heights (e.g. R1–R4).

#### III. Keyboard Parameters (Unified Configuration by Type)

1. Open the **"Keyboard Parameters"** tab
2. Left side is key type tree (automatically categorized by current KLE layout according to width, height, character positions, etc.); select a type
3. Middle edits that type's geometry (depth, angle, corner radius, edge, stabilizer, etc.) and character styles (fonts, sizes, depths for each position); can set **key color** and **text color** for that type
4. Right side 2D/3D previews that type's effect; in 2D can use menu **"Align"** for 9-grid alignment (perfectionists' dream)
5. Click **"Save and Apply"**, write that type's configuration (including colors) back to all keys of that type; then return to **"Keyboard Design"** to generate/export

#### IV. Multi-color Printing Tips (3MF)

1. Set each key's key/text colors in "Keyboard Design" or "Keyboard Parameters"
2. After full keyboard generation, use **"Export All…"** to select **3MF Merge**
3. Import the generated `.3mf` into your slicer (Bambu Studio / PrusaSlicer / Cura, etc.), **import as the same project/object**
4. In the slicer, assign different material spools/colors to different colored meshes by "Object" or "Part" (done in a few clicks in your slicer)

For more details, see [3MF Export Guide](docs/3MF导出说明.md).

---

## 📁 Project Structure Overview

```
Keycap-Generator/
├── main.py                  # Program entry (start here)
├── requirements.txt         # Dependency list (check before installing)
├── ui/                      # Interface (all UI here)
│   ├── main_window.py       # Main window & tabs (single key/keyboard design/keyboard parameters)
│   ├── parameter_panel.py   # Single key parameters (where you adjust parameters)
│   ├── batch_panel.py       # Keyboard design: spacing, height, generate/export buttons
│   ├── batch_edit_tab.py    # Keyboard parameters: type tree, configuration, 2D/3D preview
│   ├── kle_preview_widget.py# KLE 2D preview & drag selection (where you select keys)
│   ├── key_property_panel.py# Key properties & colors, apply existing scheme
│   ├── preview_widget.py    # 3D preview (VTK, where you see effects)
│   └── ...                  # Other UI components
├── core/                    # Core (core logic here)
│   ├── kle_parser.py        # KLE JSON parsing (includes c/t colors)
│   ├── batch_generator.py   # Full keyboard generation (where models are generated)
│   ├── batch_edit_config.py # Type configuration (includes colors)
│   └── ...                  # Other core modules
├── export/                  # Export (all export functions here)
│   ├── stl_exporter.py      # STL export
│   ├── step_exporter.py     # STEP export
│   └── threemf_exporter.py  # 3MF export (includes same-color merging)
├── docs/                    # Documentation (all docs here)
│   ├── 3MF导出说明.md       # Detailed 3MF export guide
│   └── KLE_default_layout.md# Built-in KLE examples
└── ...                      # Other files
```

---

## 📝 Version & Updates

- **Release V1.0**: Single key design, KLE full keyboard import, keyboard parameters configuration by type, key/text colors, apply existing scheme (dual-color preview), 3MF same-color merging, generate/cancel generation logic, etc.

For more history and details, see [CHANGELOG.md](CHANGELOG.md).

---

## 📄 License

MIT License (use however you want)

---

## 🤝 Contributing

Welcome to submit Issues and Pull Requests (report problems, contribute improvements)!
