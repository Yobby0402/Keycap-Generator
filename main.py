"""
程序入口
"""
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("机械键盘按键模型生成器")
    
    # 设置应用图标（键帽.png）
    _dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(_dir, "键帽.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建主窗口
    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
