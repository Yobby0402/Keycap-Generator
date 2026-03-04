"""
PyInstaller 运行时钩子：在程序最早阶段把解压目录加入 DLL 搜索路径，
解决 casadi 等 native 模块在 --onefile 下 "DLL load failed" 的问题。
"""
import os
import sys

def _setup_dll_path():
    if not getattr(sys, 'frozen', False):
        return
    meipass = getattr(sys, '_MEIPASS', None)
    if not meipass or not os.path.isdir(meipass):
        return
    # Python 3.8+：把解压目录加入 DLL 搜索路径，否则 _casadi.pyd 依赖的 DLL 找不到
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(meipass)
        except OSError:
            pass
        # casadi 的 .pyd 可能在 casadi 子目录，其依赖 DLL 也在该目录
        casadi_dir = os.path.join(meipass, 'casadi')
        if os.path.isdir(casadi_dir):
            try:
                os.add_dll_directory(casadi_dir)
            except OSError:
                pass
    # 同时 prepend 到 PATH，兼容旧版 Python 或部分加载器
    path_env = os.environ.get('PATH', '')
    new_path = meipass + os.pathsep + os.path.join(meipass, 'casadi') + os.pathsep + path_env
    os.environ['PATH'] = new_path

_setup_dll_path()
