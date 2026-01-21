"""
KLE 数据导入对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox, QComboBox,
                             QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal
import os

class KLEImportDialog(QDialog):
    """KLE 数据导入对话框"""
    
    # 信号：解析成功时发出
    data_parsed = pyqtSignal(list)  # 发送解析后的 KLE 数据列表
    
    # KLE预设布局数据
    KLE_PRESETS = {
        "ANSI 104": [
            ["Esc",{"x":1},"F1","F2","F3","F4",{"x":0.5},"F5","F6","F7","F8",{"x":0.5},"F9","F10","F11","F12",{"x":0.25},"PrtSc","Scroll Lock","Pause\nBreak"],
            [{"y":0.5},"~\n`","!\n1","@\n2","#\n3","$\n4","%\n5","^\n6","&\n7","*\n8","(\n9",")\n0","_\n-","+\n=",{"w":2},"Backspace",{"x":0.25},"Insert","Home","PgUp",{"x":0.25},"Num Lock","/","*","-"],
            [{"w":1.5},"Tab","Q","W","E","R","T","Y","U","I","O","P","{\n[","}\n]",{"w":1.5},"|\n\\",{"x":0.25},"Delete","End","PgDn",{"x":0.25},"7\nHome","8\n↑","9\nPgUp",{"h":2},"+"],
            [{"w":1.75},"Caps Lock","A","S","D","F","G","H","J","K","L",":\n;","\"\n'",{"w":2.25},"Enter",{"x":3.5},"4\n←","5","6\n→"],
            [{"w":2.25},"Shift","Z","X","C","V","B","N","M","<\n,",">\n.","?\n/",{"w":2.75},"Shift",{"x":1.25},"↑",{"x":1.25},"1\nEnd","2\n↓","3\nPgDn",{"h":2},"Enter"],
            [{"w":1.25},"Ctrl",{"w":1.25},"Win",{"w":1.25},"Alt",{"a":7,"w":6.25},"",{"a":4,"w":1.25},"Alt",{"w":1.25},"Win",{"w":1.25},"Menu",{"w":1.25},"Ctrl",{"x":0.25},"←","↓","→",{"x":0.25,"w":2},"0\nIns",".\nDel"]
        ],
        "ISO 105": [
            ["Esc",{"x":1},"F1","F2","F3","F4",{"x":0.5},"F5","F6","F7","F8",{"x":0.5},"F9","F10","F11","F12",{"x":0.25},"PrtSc","Scroll Lock","Pause\nBreak"],
            [{"y":0.5},"¬\n`","!\n1","\"\n2","£\n3","$\n4","%\n5","^\n6","&\n7","*\n8","(\n9",")\n0","_\n-","+\n=",{"w":2},"Backspace",{"x":0.25},"Insert","Home","PgUp",{"x":0.25},"Num Lock","/","*","-"],
            [{"w":1.5},"Tab","Q","W","E","R","T","Y","U","I","O","P","{\n[","}\n]",{"x":0.25,"w":1.25,"h":2,"w2":1.5,"h2":1,"x2":-0.25},"Enter",{"x":0.25},"Delete","End","PgDn",{"x":0.25},"7\nHome","8\n↑","9\nPgUp",{"h":2},"+"],
            [{"w":1.75},"Caps Lock","A","S","D","F","G","H","J","K","L",":\n;","@\n'","~\n#",{"x":4.75},"4\n←","5","6\n→"],
            [{"w":1.25},"Shift","|\n\\","Z","X","C","V","B","N","M","<\n,",">\n.","?\n/",{"w":2.75},"Shift",{"x":1.25},"↑",{"x":1.25},"1\nEnd","2\n↓","3\nPgDn",{"h":2},"Enter"],
            [{"w":1.25},"Ctrl",{"w":1.25},"Win",{"w":1.25},"Alt",{"a":7,"w":6.25},"",{"a":4,"w":1.25},"AltGr",{"w":1.25},"Win",{"w":1.25},"Menu",{"w":1.25},"Ctrl",{"x":0.25},"←","↓","→",{"x":0.25,"w":2},"0\nIns",".\nDel"]
        ],
        "Default 60%": [
            ["~\n`","!\n1","@\n2","#\n3","$\n4","%\n5","^\n6","&\n7","*\n8","(\n9",")\n0","_\n-","+\n=",{"w":2},"Backspace"],
            [{"w":1.5},"Tab","Q","W","E","R","T","Y","U","I","O","P","{\n[","}\n]",{"w":1.5},"|\n\\"],
            [{"w":1.75},"Caps Lock","A","S","D","F","G","H","J","K","L",":\n;","\"\n'",{"w":2.25},"Enter"],
            [{"w":2.25},"Shift","Z","X","C","V","B","N","M","<\n,",">\n.","?\n/",{"w":2.75},"Shift"],
            [{"w":1.25},"Ctrl",{"w":1.25},"Win",{"w":1.25},"Alt",{"a":7,"w":6.25},"",{"a":4,"w":1.25},"Alt",{"w":1.25},"Win",{"w":1.25},"Menu",{"w":1.25},"Ctrl"]
        ],
        "JD 40": [
            ["Esc","Q","W","E","R","T","Y","U","I","O","P","Back<br>Space"],
            [{"w":1.25},"Tab","A","S","D","F","G","H","J","K","L",{"w":1.75},"Enter"],
            [{"w":1.75},"Shift","Z","X","C","V","B","N","M","<\n.",{"w":1.25},"Shift","Fn"],
            [{"w":1.25},"Hyper","Super","Meta",{"a":7,"w":6.25},"",{"a":4,"w":1.25},"Meta",{"w":1.25},"Super"]
        ],
        "Planck": [
            [{"a":7},"Tab","Q","W","E","R","T","Y","U","I","O","P","Back Space"],
            ["Esc","A","S","D","F","G","H","J","K","L",";","'"],
            ["Shift","Z","X","C","V","B","N","M",",",".","/","Return"],
            ["","Ctrl","Alt","Super","&dArr;",{"w":2},"","&uArr;","&larr;","&darr;","&uarr;","&rarr;"]
        ],
        "Keycool 84": [
            [{"a":6},"Esc","F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",{"a":5},"PrtSc\nNmLk","Pause\nScrLk","Delete\nInsert"],
            [{"a":4},"~\n`","!\n1","@\n2","#\n3","$\n4","%\n5","^\n6","&\n7","*\n8","(\n9",")\n0","_\n-","+\n=",{"a":6,"w":2},"Backspace","Home"],
            [{"a":4,"w":1.5},"Tab","Q","W","E","R","T","Y","U","I","O","P","{\n[","}\n]",{"w":1.5},"|\n\\",{"a":6},"Page Up"],
            [{"a":4,"w":1.75},"Caps Lock","A","S","D","F","G","H","J","K","L",":\n;","\"\n'",{"a":6,"w":2.25},"Enter","Page Down"],
            [{"w":2.25},"Shift",{"a":4},"Z","X","C","V","B","N","M","<\n,",">\n.","?\n/",{"a":6,"w":1.75},"Shift",{"a":7},"↑",{"a":6},"End"],
            [{"w":1.25},"Ctrl",{"w":1.25},"Win",{"w":1.25},"Alt",{"a":7,"w":6.25},"",{"a":6},"Alt","Fn","Ctrl",{"a":7},"←","↓","→"]
        ],
        "Leopold FC660M": [
            ["~\n`","!\n1","@\n2","#\n3","$\n4","%\n5","^\n6","&\n7","*\n8","(\n9",")\n0","_\n-","+\n=",{"w":2},"Backspace",{"x":0.5},"Insert"],
            [{"w":1.5},"Tab","Q","W","E","R","T","Y","U","I","O","P","{\n[","}\n]",{"w":1.5},"|\n\\",{"x":0.5},"Delete"],
            [{"w":1.75},"Caps Lock","A","S","D","F","G","H","J","K","L",":\n;","\"\n'",{"w":2.25},"Enter"],
            [{"w":2.25},"Shift","Z","X","C","V","B","N","M","<\n,",">\n.","?\n/",{"w":2.25},"Shift","↑"],
            [{"w":1.25},"Ctrl","Win",{"w":1.25},"Alt",{"a":7,"w":6.25},"",{"a":4,"w":1.25},"Alt",{"w":1.25},"Ctrl",{"w":1.25},"Menu","←","↓","→"]
        ]
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入 KLE 布局数据")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 预设选择区域
        preset_group = QGroupBox("预设布局（可选）")
        preset_layout = QVBoxLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("无预设（手动粘贴）", None)
        for preset_name in self.KLE_PRESETS.keys():
            self.preset_combo.addItem(preset_name, preset_name)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(QLabel("选择预设布局:"))
        preset_layout.addWidget(self.preset_combo)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # 说明标签
        info_label = QLabel("请粘贴从 keyboard-layout-editor.com 导出的 Raw Data:")
        layout.addWidget(info_label)
        
        # 文本输入框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此粘贴 KLE Raw Data... 或从上方选择预设布局")
        self.text_edit.setAcceptRichText(False)
        layout.addWidget(self.text_edit, stretch=1)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.parse_btn = QPushButton("解析并导入")
        self.parse_btn.setDefault(True)
        self.parse_btn.clicked.connect(self.parse_and_accept)
        btn_layout.addWidget(self.parse_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.text_edit.clear)
        btn_layout.addWidget(self.clear_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def on_preset_selected(self, index):
        """当选择预设时，自动填充文本"""
        preset_name = self.preset_combo.itemData(index)
        if preset_name and preset_name in self.KLE_PRESETS:
            # 将预设数据转换为JSON字符串
            import json
            preset_data = self.KLE_PRESETS[preset_name]
            # 转换为JSON字符串（KLE使用Dirty JSON格式，但我们可以直接使用json.dumps）
            json_str = json.dumps(preset_data, ensure_ascii=False, indent=2)
            self.text_edit.setPlainText(json_str)
            self.text_edit.setFocus()
    
    def parse_and_accept(self):
        """解析数据并关闭对话框"""
        raw_text = self.text_edit.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "警告", "请输入 KLE Raw Data 或选择预设布局")
            return
            
        try:
            # 直接使用 KLEParser，它会自动处理 Dirty JSON
            from core.kle_parser import KLEParser
            parser = KLEParser()
            
            # 尝试解析为JSON，如果失败则直接使用字符串
            try:
                import json
                parsed_data = json.loads(raw_text)
                keys = parser.parse(parsed_data)  # 传入已解析的数据
            except:
                keys = parser.parse(raw_text)  # 传入字符串，让parser处理
            
            if keys:
                self.data_parsed.emit(keys)
                self.accept()  # 关闭对话框
            else:
                QMessageBox.warning(self, "警告", "未找到有效的按键数据\n\n可能的原因：\n1. JSON 格式不正确\n2. 数据为空或格式不匹配")
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            # 输出到终端而不是弹窗
            print("=" * 60)
            print("KLE 解析错误:")
            print("=" * 60)
            print(f"错误信息: {str(e)}")
            print("\n详细堆栈:")
            print(error_detail)
            print("=" * 60)
            QMessageBox.critical(self, "错误", f"解析出错，详细信息已输出到终端\n\n错误: {str(e)}")
