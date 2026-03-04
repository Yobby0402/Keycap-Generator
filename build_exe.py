"""
打包脚本：将程序打包为exe文件
使用方法：python build_exe.py

若 casadi 报错 "DLL load failed"，可改为单目录模式：USE_ONEDIR = True
（生成 dist/机械键盘按键模型生成器/ 目录，内含 exe 与依赖，DLL 加载更稳定）
"""
import os
import sys
import subprocess
import shutil

# 改为 True 则打包为目录模式（非单文件），可避免 casadi 等 native DLL 在单文件下加载失败
USE_ONEDIR = False

def main():
    """主函数"""
    # 获取当前目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
    except ImportError:
        print("错误：未安装 PyInstaller")
        print("请运行: pip install pyinstaller")
        sys.exit(1)
    
    # 检查图标文件是否存在
    icon_path = os.path.join(base_dir, "键帽.png")
    if not os.path.exists(icon_path):
        print(f"警告：图标文件不存在: {icon_path}")
        print("将继续打包，但不会设置图标")
        icon_path = None
    
    # 清理之前的构建文件
    print("清理之前的构建文件...")
    for dir_name in ['build', 'dist', '__pycache__']:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"  已删除: {dir_path}")
    
    # 清理spec文件
    spec_file = os.path.join(base_dir, "main.spec")
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"  已删除: {spec_file}")
    
    # 构建PyInstaller命令
    cmd = [
        'pyinstaller',
        '--name=机械键盘按键模型生成器',  # exe文件名
        '--windowed',  # 无控制台窗口（等同于--noconsole）
        '--clean',  # 清理临时文件
        '--noconfirm',  # 覆盖输出目录而不询问
        '--noupx',  # 不使用UPX压缩（避免兼容性问题）
    ]
    if USE_ONEDIR:
        # 目录模式：exe 与依赖在同一目录，DLL 加载更稳定（尤其 casadi）
        print("使用目录模式打包 (USE_ONEDIR=True)")
    else:
        cmd.append('--onefile')  # 单文件模式
    
    # 添加图标
    if icon_path:
        cmd.append(f'--icon={icon_path}')
        print(f"使用图标: {icon_path}")
    
    # 添加数据文件（config.json等）
    # Windows使用分号分隔，Linux/Mac使用冒号
    data_files = []
    config_file = os.path.join(base_dir, "config.json")
    if os.path.exists(config_file):
        data_files.append(f'{config_file};.')
        print(f"添加数据文件: config.json")
    
    # 添加图标文件到数据文件（程序运行时可能需要访问）
    if icon_path:
        data_files.append(f'{icon_path};.')
        print(f"添加图标文件到数据: 键帽.png")
    
    # 添加数据文件到命令
    for data in data_files:
        cmd.append(f'--add-data={data}')
    
    # casadi 是 CadQuery 的依赖，包含 native DLL（_casadi.pyd），必须整包收集
    try:
        import casadi
        cmd.append('--collect-all=casadi')
        print("添加: --collect-all=casadi (包含 DLL)")
    except ImportError:
        pass
    
    # 运行时钩子：启动时把 PyInstaller 解压目录加入 DLL 搜索路径，解决 _casadi 等 DLL 加载失败
    runtime_hook = os.path.join(base_dir, "pyi_runtime_hook_dll_path.py")
    if os.path.exists(runtime_hook):
        cmd.append(f'--runtime-hook={runtime_hook}')
        print("添加: 运行时钩子 (DLL 搜索路径)")
    
    # 添加隐藏导入（PyInstaller可能无法自动检测的模块）
    hidden_imports = [
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtOpenGL',
        'cadquery',
        'cadquery.occ_impl',
        'cadquery.occ_impl.geom',
        'cadquery.occ_impl.shapes',
        'cadquery.occ_impl.solver',  # 会拉入 casadi
        'casadi',  # CadQuery 依赖，含 native DLL
        'vtk',
        'vtkmodules',
        'vtkmodules.all',
        'vtkmodules.qt.QVTKRenderWindowInteractor',
        'fontTools',
        'fontTools.ttLib',
        'shapely',
        'shapely.geometry',
        'numpy',
        'PIL',
        'PIL.Image',
        'cv2',  # opencv-python
        'trimesh',  # 3MF 导出
        'networkx',  # trimesh 依赖
        'lxml',  # trimesh 导出 3MF 时依赖
    ]
    for imp in hidden_imports:
        cmd.append(f'--hidden-import={imp}')
    
    # 排除不需要的模块（减小文件大小）
    excludes = [
        'matplotlib',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
    ]
    for exc in excludes:
        cmd.append(f'--exclude-module={exc}')
    
    # 添加主程序文件
    cmd.append('main.py')
    
    # 打印命令
    print("\n执行打包命令:")
    print(" ".join(cmd))
    print("\n开始打包...\n")
    
    # 执行打包
    try:
        result = subprocess.run(cmd, check=True, cwd=base_dir)
        print("\n[OK] 打包成功！")
        if USE_ONEDIR:
            out_dir = os.path.join(base_dir, 'dist', '机械键盘按键模型生成器')
            print(f"\n输出目录: {out_dir}")
            print(f"运行: {os.path.join(out_dir, '机械键盘按键模型生成器.exe')}")
        else:
            print(f"\n输出文件: {os.path.join(base_dir, 'dist', '机械键盘按键模型生成器.exe')}")
        print("\n提示：")
        print("  - 首次运行可能需要几秒钟加载")
        print("  - 若仍报 casadi DLL 错误，请将 build_exe.py 顶部 USE_ONEDIR 改为 True 后重新打包")
    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] 打包失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n打包被用户中断")
        sys.exit(1)

if __name__ == "__main__":
    main()
