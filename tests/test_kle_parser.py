import unittest
import json
import sys
import os

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.kle_parser import KLEParser, KLEKey

class TestKLEParser(unittest.TestCase):
    def setUp(self):
        self.parser = KLEParser()

    def test_basic_parsing(self):
        """测试基本按键解析"""
        json_data = [
            ["Esc", "Q", "W"]
        ]
        keys = self.parser.parse(json_data)
        self.assertEqual(len(keys), 3)
        self.assertEqual(keys[0].labels[0], "Esc")
        self.assertEqual(keys[0].x, 0.0)
        self.assertEqual(keys[1].labels[0], "Q")
        self.assertEqual(keys[1].x, 1.0)
        self.assertEqual(keys[2].labels[0], "W")
        self.assertEqual(keys[2].x, 2.0)

    def test_property_changes(self):
        """测试属性变更 (x, w)"""
        json_data = [
            [{'x': 1}, "A", {'w': 2}, "B"]
        ]
        keys = self.parser.parse(json_data)
        self.assertEqual(len(keys), 2)
        
        # A: x=1, w=1
        self.assertEqual(keys[0].labels[0], "A")
        self.assertEqual(keys[0].x, 1.0)
        self.assertEqual(keys[0].width, 1.0)
        
        # B: x=1+1=2, w=2
        self.assertEqual(keys[1].labels[0], "B")
        self.assertEqual(keys[1].x, 2.0)
        self.assertEqual(keys[1].width, 2.0)

    def test_multiline(self):
        """测试多行布局"""
        json_data = [
            ["1"],
            ["2"]
        ]
        keys = self.parser.parse(json_data)
        self.assertEqual(len(keys), 2)
        
        self.assertEqual(keys[0].labels[0], "1")
        self.assertEqual(keys[0].y, 0.0)
        
        self.assertEqual(keys[1].labels[0], "2")
        self.assertEqual(keys[1].y, 1.0) # 第二行 y+1

    def test_complex_enter_key(self):
        """测试复杂按键 (如 ISO Enter)"""
        # 这是一个模拟 ISO Enter 的简化例子
        json_data = [
            [{'w':1.5}, "Enter"],
            [{'w':1.25, 'x':0.25, 'h':2, 'w':0.25}, ""] # 并不是真实的 ISO Enter，只是测试 w/h/x 组合
        ]
        keys = self.parser.parse(json_data)
        self.assertEqual(keys[0].width, 1.5)
        self.assertEqual(keys[1].height, 2.0)

if __name__ == '__main__':
    unittest.main()
