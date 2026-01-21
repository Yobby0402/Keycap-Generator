"""
KLE (Keyboard Layout Editor) JSON 解析器
用于将 KLE 的原始数据转换为内部的按键实例列表
"""
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union

@dataclass
class KLEKey:
    """单个按键的中间表示"""
    # 位置和尺寸 (u单位)
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    
    # 旋转
    rotation_angle: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    
    # 内容
    labels: List[str] = field(default_factory=list)
    text_color: str = "#000000"
    key_color: str = "#cccccc"
    
    # 样式元数据
    font_sizes: List[float] = field(default_factory=list)
    alignment: int = 4  # KLE alignment standard (0-11, 4 is center)
    
    # 原始属性 (用于调试或高级处理)
    profile: str = ""  # 键帽高度配置 (e.g. "DSA", "R3")
    row: int = 0       # 物理行号


class KLEParser:
    """解析 KLE JSON 数据"""
    
    def parse(self, json_data: Union[str, List]) -> List[KLEKey]:
        """
        解析 JSON 数据并返回 KLEKey 列表
        
        参数:
            json_data: JSON 字符串或已解析的列表
        """
        if isinstance(json_data, str):
            try:
                # 尝试直接解析标准 JSON
                data = json.loads(json_data)
            except json.JSONDecodeError as e1:
                # 尝试修复非标准 JSON (Dirty JSON)
                try:
                    fixed_json = self._fix_dirty_json(json_data)
                    data = json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    # 输出详细错误信息用于调试
                    error_msg = f"JSON 解析失败\n\n原始错误: {e1}\n修复后错误: {e2}\n修复后的 JSON 前500字符:\n{fixed_json[:500]}..."
                    print("=" * 60)
                    print("KLE JSON 解析错误详情:")
                    print("=" * 60)
                    print(error_msg)
                    print("=" * 60)
                    raise ValueError(error_msg) from e2
                except Exception as e3:
                    error_msg = f"修复 JSON 时出错: {e3}"
                    print("=" * 60)
                    print("KLE JSON 修复错误:")
                    print("=" * 60)
                    import traceback
                    traceback.print_exc()
                    print("=" * 60)
                    raise ValueError(error_msg) from e3
        else:
            data = json_data

        keys: List[KLEKey] = []
        
        # 初始状态
        current = {
            'x': 0.0, 'y': 0.0,
            'w': 1.0, 'h': 1.0,
            'r': 0.0, 'rx': 0.0, 'ry': 0.0,
            'c': "#cccccc", 't': "#000000",
            'a': 4, 'f': 3, 'fa': [],
            'p': ""
        }
        
        # 游标位置
        cursor_x = 0.0
        cursor_y = 0.0
        
        # 遍历每一行
        for row_idx, row in enumerate(data):
            if isinstance(row, dict):
                # 可能是顶层的元数据，跳过或处理
                continue
                
            # 每新起一行，重置 X
            cursor_x = current['x'] # 通常是0，或者是上一行结束后的设置？
            # 实际上 KLE 每一行都重置 X 到 current_rotation_x (默认0)
            # 但如果只有部分行被旋转，逻辑会复杂。
            # 简化逻辑：每行开始时，x 重置为 rotation_x (通常是0)
            # y 递增
            
            # 在行内遍历
            for item in row:
                if isinstance(item, dict):
                    # 更新状态
                    # 处理相对坐标变化
                    if 'x' in item: cursor_x += item['x']
                    if 'y' in item: cursor_y += item['y']
                    
                    # 更新当前属性
                    if 'w' in item: current['w'] = item['w']
                    if 'h' in item: current['h'] = item['h']
                    if 'a' in item: current['a'] = item['a']
                    if 'f' in item: 
                        current['f'] = item['f']
                        current['fa'] = [] # 重置字体大小数组
                    if 'fa' in item: current['fa'] = item['fa']
                    if 'p' in item: current['p'] = item['p']
                    if 'c' in item: current['c'] = item['c']
                    if 't' in item: current['t'] = item['t']
                    
                    # 旋转处理 (如果遇到旋转属性，不仅更新状态，还要重置当前坐标原点)
                    if 'r' in item: 
                        current['r'] = item['r']
                        # 旋转通常伴随着 rx/ry 的设定
                        current['rx'] = item.get('rx', current['rx'])
                        current['ry'] = item.get('ry', current['ry'])
                        
                        # 当旋转发生变化时，KLE 重置坐标参考系
                        cursor_x = current['rx']
                        cursor_y = current['ry']
                        
                        # 处理当前项里的额外偏移（因为重置了）
                        if 'x' in item: cursor_x += item['x']
                        if 'y' in item: cursor_y += item['y']
                    
                    # 单独的 rx/ry 更新 (不常见，通常跟 r 一起)
                    elif 'rx' in item or 'ry' in item:
                        current['rx'] = item.get('rx', current['rx'])
                        current['ry'] = item.get('ry', current['ry'])
                        cursor_x = current['rx']
                        cursor_y = current['ry']
                        if 'x' in item: cursor_x += item['x']
                        if 'y' in item: cursor_y += item['y']
                        
                elif isinstance(item, str):
                    # 创建按键
                    key = KLEKey(
                        x=cursor_x,
                        y=cursor_y,
                        width=current['w'],
                        height=current['h'],
                        rotation_angle=current['r'],
                        rotation_x=current['rx'],
                        rotation_y=current['ry'],
                        labels=self._parse_labels(item),
                        key_color=current['c'],
                        text_color=current['t'],
                        alignment=current['a'],
                        profile=current['p'],
                        row=row_idx
                    )
                    
                    # 计算字体大小列表
                    # KLE 逻辑：如果 fa 存在，使用 fa；否则使用 f
                    # 这里的逻辑比较简化，实际 KLE 渲染器有复杂的继承逻辑
                    default_size = current['f']
                    font_sizes = current.get('fa', [])
                    
                    # 填充 font_sizes 使其与 labels 长度匹配
                    # 这里先简单存储，后续处理
                    key.font_sizes = font_sizes if font_sizes else [default_size] * 12
                    
                    keys.append(key)
                    
                    # 移动游标
                    cursor_x += current['w']
                    
                    # 重置单次生效的属性 (w, h) 到默认值 1.0
                    current['w'] = 1.0
                    current['h'] = 1.0
            
            # 行结束，移动 Y
            cursor_y += 1.0
        
        return keys

    def _parse_labels(self, label_str: str) -> List[str]:
        """
        解析标签字符串，处理换行符
        
        KLE 的字符位置规则（12个位置）：
        顶面：左上0, 中上8, 右上2, 左中6, 正中9, 右中7, 左下1, 中下10, 右下3
        侧刻：左侧4, 中间11, 右侧5
        
        字符串用 \n 分隔，索引对应位置。字符串会在最后一个非空字符处截断。
        例如："Q\n\n1" 表示位置0是"Q"，位置2是"1"，其他位置为空。
        
        注意：
        1. 如果 label_str 中包含字面量 "\\n"（两个字符），需要先转换为真正的换行符
        2. 如果字符串没有换行符（如"Shift"），默认放在位置9（正中）
        """
        # 处理字面量 \n（JSON 解析后可能是 "\\n"）
        # 将 "\\n" 转换为真正的换行符
        # 同时处理 HTML 的 <br> 标签（转换为换行符）
        if isinstance(label_str, str):
            # 先处理 HTML 的 <br> 标签（不区分大小写）
            import re
            label_str = re.sub(r'<br\s*/?>', '\n', label_str, flags=re.IGNORECASE)
            # 替换字面量 \n（转义后的）
            label_str = label_str.replace('\\n', '\n')
        
        # 分割字符串
        parts = label_str.split('\n')
        
        # 如果只有一个部分且没有换行符，说明是单个字符串（如"Shift"）
        # 根据KLE规则，应该放在位置9（正中）
        if len(parts) == 1 and '\n' not in label_str:
            labels = [''] * 12
            if parts[0] and parts[0].strip():
                labels[9] = parts[0].strip()  # 放在正中位置
            return labels
        
        # 找到最后一个非空字符的索引
        last_non_empty = -1
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] and parts[i].strip():
                last_non_empty = i
                break
        
        # 如果找到了非空字符，只保留到该位置（KLE 会在最后一个非空字符处截断）
        if last_non_empty >= 0:
            parts = parts[:last_non_empty + 1]
        
        # KLE 最多支持12个位置（索引0-11）
        # 如果分割后的列表少于12个，用空字符串填充到12个
        labels = parts[:12]  # 最多取12个
        
        # 如果少于12个，填充到12个
        while len(labels) < 12:
            labels.append('')
        
        return labels

    def _fix_dirty_json(self, raw: str) -> str:
        """
        修复 KLE 的非标准 JSON (Dirty JSON)
        1. 给属性名加上引号 (如 {a:1} -> {"a":1})
        2. 确保外层是合法的数组
        3. 处理字符串中的换行符（需要转义）
        """
        # 1. 移除多余的空白字符（但保留字符串内的内容）
        text = raw.strip()
        
        # 2. 先保护字符串内容，避免在字符串内部进行替换
        # 使用占位符替换字符串内容
        string_placeholders = {}
        placeholder_counter = 0
        
        def replace_string(match):
            nonlocal placeholder_counter
            placeholder = f"__STRING_PLACEHOLDER_{placeholder_counter}__"
            full_match = match.group(0)
            # 提取字符串内容（去掉首尾引号）
            if full_match.startswith('"') and full_match.endswith('"'):
                string_content = full_match[1:-1]
            else:
                string_content = full_match
            
            # 转义字符串中的特殊字符
            # 注意：顺序很重要！先处理真正的控制字符，再处理反斜杠和引号
            # 这样可以避免将已转义的控制字符再次转义
            string_content = string_content.replace('\\', '\\\\')  # 先转义反斜杠（包括已转义的 \n）
            # 然后处理真正的控制字符（这些不会被 \\ 匹配到，因为已经被转义了）
            # 但要注意：如果原始字符串中有字面量 \n（两个字符），上面的替换已经把它变成了 \\n
            # 所以这里只需要处理真正的换行符
            # 实际上，由于先替换了 \\，字面量 \n 已经变成 \\n，真正的 \n 还是 \n
            # 所以我们可以安全地替换真正的控制字符
            string_content = string_content.replace('\n', '\\n')   # 转义真正的换行符
            string_content = string_content.replace('\r', '\\r')   # 转义真正的回车符
            string_content = string_content.replace('\t', '\\t')   # 转义真正的制表符
            string_content = string_content.replace('"', '\\"')   # 转义引号
            
            string_placeholders[placeholder] = f'"{string_content}"'
            placeholder_counter += 1
            return placeholder
        
        # 匹配字符串（引号内的内容，支持转义字符）
        # 这个正则匹配从 " 开始到 " 结束的字符串，支持 \" 转义
        string_pattern = r'"(?:[^"\\]|\\.)*"'
        text = re.sub(string_pattern, replace_string, text)
        
        # 3. 正则替换：给键加上引号
        # 匹配模式：
        # ({ 或 ,) 后面跟空白，然后是单词字符(键名)，然后是冒号
        # 替换为： \1"\2":
        pattern = r'([\{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)'
        fixed = re.sub(pattern, r'\1"\2"\3', text)
        
        # 4. 恢复字符串内容
        for placeholder, original_string in string_placeholders.items():
            fixed = fixed.replace(placeholder, original_string)
        
        # 5. 处理没有外层括号的情况
        # 很多时候复制出来的内容是 [row1], [row2] 这样的格式
        # 检测模式：], 后面跟着换行或空格，然后是 [
        import re as re_module
        if re_module.search(r'\],\s*\[', fixed) and not (fixed.strip().startswith('[[') and fixed.strip().endswith(']]')):
             # 如果检测到多个数组，但没有外层数组包裹，则添加
             fixed = f"[{fixed}]"
        
        return fixed
