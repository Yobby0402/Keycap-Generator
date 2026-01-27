"""
按键模型生成器
整合按键本体、文字和图片模型的生成
"""
import cadquery as cq
from core.parameters import KeycapParameters
from geometry.keycap_shape import KeycapShape
from geometry.text_extrusion import TextExtrusion
from geometry.image_extrusion import ImageExtrusion


class KeycapModeler:
    """按键模型生成器主类"""
    
    def __init__(self, params: KeycapParameters):
        self.params = params
        self.keycap_shape = KeycapShape(params)
        self.text_extrusion = TextExtrusion(params)
        self.image_extrusion = ImageExtrusion(params)
    
    def generate(self) -> tuple:
        """
        生成完整的按键模型

        返回:
            (按键本体模型, 文字模型, 图片镶嵌体) 或 (None, None, None) 如果生成失败。
            图片镶嵌体：当存在 depth>0 的图片凹陷时有值，用于双色打印填充；否则为 None。
        """
        try:
            # 验证参数
            is_valid, error_msg = self.params.validate()
            if not is_valid:
                print(f"参数验证失败: {error_msg}")
                return None, None, None

            # 若有文字且启用弧面：先生成键帽（不含弧面），再对弧面体做文字布尔后与键帽合并，使文字完全贴合弧面
            has_text = False
            if self.params.text_items:
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
            
            curved_enabled = getattr(self.params.geometry, 'curved_top_enabled', False)
            use_curved_text_flow = has_text and curved_enabled
            
            if use_curved_text_flow:
                self.keycap_shape._skip_curved_this_build = True
            
            print("开始生成按键本体...")
            keycap_body = self.keycap_shape.generate_keycap_body()
            if use_curved_text_flow:
                self.keycap_shape._skip_curved_this_build = False

            if keycap_body is None:
                print("错误：按键本体生成失败")
                return None, None, None
            
            print(f"按键本体生成成功（尺寸: {self.params.key_width}x{self.params.key_height}x{self.params.key_depth}mm）")
            
            if has_text:
                print(f"开始生成文字模型（字体: {self.params.font_path or '使用text_items中的字体'}）")
                if use_curved_text_flow:
                    curved_part, is_convex = self.keycap_shape.build_curved_surface_only()
                    keycap_body, text_model = self.text_extrusion.apply_text_to_keycap(
                        keycap_body, (curved_part, is_convex)
                    )
                else:
                    keycap_body, text_model = self.text_extrusion.apply_text_to_keycap(keycap_body)
                if not use_curved_text_flow and text_model is None:
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
            
            # 生成并应用图片（支持 image_items），并收集凹陷时的镶嵌体 inlay
            image_items = getattr(self.params, 'image_items', None) or []
            image_inlay = None
            if image_items:
                print(f"开始应用图片（共 {len(image_items)} 张）")
                keycap_body, _, image_inlay = self.image_extrusion.apply_images_to_keycap(keycap_body)

            print("模型生成完成")
            return keycap_body, text_model, image_inlay

        except Exception as e:
            print(f"生成模型时出错: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None
    
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
