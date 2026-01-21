"""
按键模型生成器
整合按键本体和文字模型的生成
"""
import cadquery as cq
from core.parameters import KeycapParameters
from geometry.keycap_shape import KeycapShape
from geometry.text_extrusion import TextExtrusion


class KeycapModeler:
    """按键模型生成器主类"""
    
    def __init__(self, params: KeycapParameters):
        self.params = params
        self.keycap_shape = KeycapShape(params)
        self.text_extrusion = TextExtrusion(params)
    
    def generate(self) -> tuple:
        """
        生成完整的按键模型
        
        返回:
            (按键本体模型, 文字模型) 或 (None, None) 如果生成失败
        """
        try:
            # 验证参数
            is_valid, error_msg = self.params.validate()
            if not is_valid:
                print(f"参数验证失败: {error_msg}")
                return None, None
            
            # 生成按键本体
            print("开始生成按键本体...")
            keycap_body = self.keycap_shape.generate_keycap_body()
            
            if keycap_body is None:
                print("错误：按键本体生成失败")
                return None, None
            
            print(f"按键本体生成成功（尺寸: {self.params.key_width}x{self.params.key_height}x{self.params.key_depth}mm）")
            
            # 生成文字模型
            # 检查是否有文字项（支持新的 text_items 结构）
            has_text = False
            if self.params.text_items:
                # 检查是否有有效的文字项
                for item in self.params.text_items:
                    if isinstance(item, dict):
                        txt = item.get('text', '')
                        font = item.get('font', self.params.font_path)
                    else:
                        txt = item.text if hasattr(item, 'text') else ''
                        font = item.font_path if hasattr(item, 'font_path') and item.font_path else self.params.font_path
                    if txt and font:
                        has_text = True
                        break
            elif self.params.font_path and self.params.letter:
                # 兼容旧模式
                has_text = True
            
            if has_text:
                print(f"开始生成文字模型（字体: {self.params.font_path or '使用text_items中的字体'}）")
                keycap_body, text_model = self.text_extrusion.apply_text_to_keycap(keycap_body)
                if text_model is None:
                    print("警告：文字模型生成失败，但按键本体已生成")
            else:
                print(f"未设置字体或字母，跳过文字生成")
                print(f"  - font_path: {self.params.font_path}")
                print(f"  - letter: {self.params.letter}")
                print(f"  - text_items 数量: {len(self.params.text_items) if self.params.text_items else 0}")
                if self.params.text_items:
                    for i, item in enumerate(self.params.text_items):
                        if isinstance(item, dict):
                            print(f"  - text_items[{i}]: text='{item.get('text', '')}', font='{item.get('font', '')}'")
                        else:
                            print(f"  - text_items[{i}]: text='{item.text if hasattr(item, 'text') else ''}', font='{item.font_path if hasattr(item, 'font_path') else ''}'")
                text_model = None
            
            print("模型生成完成")
            return keycap_body, text_model
            
        except Exception as e:
            print(f"生成模型时出错: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def generate_keycap_only(self) -> cq.Workplane:
        """仅生成按键本体（不含文字）"""
        try:
            is_valid, error_msg = self.params.validate()
            if not is_valid:
                print(f"参数验证失败: {error_msg}")
                return None
            
            return self.keycap_shape.generate_keycap_body()
        except Exception as e:
            print(f"生成按键模型时出错: {e}")
            return None
    
    def generate_text_only(self) -> cq.Workplane:
        """仅生成文字模型"""
        try:
            if not self.params.font_path or not self.params.letter:
                return None
            
            return self.text_extrusion.generate_text_model()
        except Exception as e:
            print(f"生成文字模型时出错: {e}")
            return None
