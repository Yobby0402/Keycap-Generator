# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('g:\\Code\\Keycap-Generator\\config.json', '.'), ('g:\\Code\\Keycap-Generator\\键帽.png', '.')]
binaries = []
hiddenimports = ['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtOpenGL', 'cadquery', 'cadquery.occ_impl', 'cadquery.occ_impl.geom', 'cadquery.occ_impl.shapes', 'cadquery.occ_impl.solver', 'casadi', 'vtk', 'vtkmodules', 'vtkmodules.all', 'vtkmodules.qt.QVTKRenderWindowInteractor', 'fontTools', 'fontTools.ttLib', 'shapely', 'shapely.geometry', 'numpy', 'PIL', 'PIL.Image', 'cv2', 'trimesh', 'networkx', 'lxml']
tmp_ret = collect_all('casadi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['g:\\Code\\Keycap-Generator\\pyi_runtime_hook_dll_path.py'],
    excludes=['matplotlib', 'pandas', 'scipy', 'IPython', 'jupyter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='机械键盘按键模型生成器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['g:\\Code\\Keycap-Generator\\键帽.png'],
)
