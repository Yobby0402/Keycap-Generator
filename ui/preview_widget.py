"""
VTK 3D预览组件
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import cadquery as cq
import numpy as np


class PreviewWidget(QWidget):
    """3D模型预览组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.keycap_actor = None
        self.text_actor = None
        self.all_keycap_actors = []  # 用于存储多个按键的actor
        self.all_text_actors = []  # 用于存储多个文字的actor
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建VTK渲染窗口
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget)
        
        # 创建渲染器
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.2, 0.2, 0.3)  # 深蓝色背景
        
        # 创建渲染窗口
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        
        # 添加交互器样式
        self.interactor_style = vtk.vtkInteractorStyleTrackballCamera()
        self.vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(
            self.interactor_style
        )
        
        # 添加坐标轴（右上角小窗口）
        self.axes = vtk.vtkAxesActor()
        self.axes_widget = vtk.vtkOrientationMarkerWidget()
        self.axes_widget.SetOrientationMarker(self.axes)
        self.axes_widget.SetInteractor(self.vtk_widget.GetRenderWindow().GetInteractor())
        self.axes_widget.SetEnabled(True)
        self.axes_widget.InteractiveOn()
        
        # 初始化基准面和原点标记
        self.origin_actor = None
        self.xy_plane_actor = None
        self.xz_plane_actor = None
        self.yz_plane_actor = None
        
        # 添加坐标原点标记（在场景中心）
        self.add_origin_marker()
        
        # 添加三个基准面（XY, XZ, YZ平面）
        self.add_reference_planes()
        
        # 初始化相机
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def update_text_offset(self, dx: float, dy: float):
        """
        更新文字模型的显示偏移（不需要重新生成）
        
        参数:
            dx: X轴偏移增量 (相对于生成时的位置)
            dy: Y轴偏移增量
        """
        if self.text_actor:
            self.text_actor.SetPosition(dx, dy, 0)
            self.vtk_widget.GetRenderWindow().Render()
    
    def update_model(self, keycap_model: cq.Workplane = None, 
                     text_model: cq.Workplane = None):
        """
        更新显示的模型（单个按键）
        
        参数:
            keycap_model: 按键模型
            text_model: 文字模型
        """
        # 清除现有模型
        if self.keycap_actor:
            self.renderer.RemoveActor(self.keycap_actor)
            self.keycap_actor = None
        
        if self.text_actor:
            self.renderer.RemoveActor(self.text_actor)
            self.text_actor = None
        
        # 清除所有按键模型
        self.clear_all_models()
        
        # 添加按键模型
        if keycap_model is not None:
            self.keycap_actor = self._cq_to_vtk_actor(keycap_model, color=(0.8, 0.8, 0.8))
            if self.keycap_actor:
                self.renderer.AddActor(self.keycap_actor)
        
        # 添加文字模型
        if text_model is not None:
            self.text_actor = self._cq_to_vtk_actor(text_model, color=(1.0, 0.0, 0.0))
            if self.text_actor:
                self.renderer.AddActor(self.text_actor)
        
        # 重置相机并渲染
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def update_all_models(self, keycap_models: list, text_models: list):
        """
        更新显示所有按键的模型（批量预览）
        
        参数:
            keycap_models: 按键模型列表 [(model, position), ...]，position是(x, y, z)元组
            text_models: 文字模型列表 [(model, position), ...]
        """
        # 清除现有模型
        self.clear_all_models()
        if self.keycap_actor:
            self.renderer.RemoveActor(self.keycap_actor)
            self.keycap_actor = None
        if self.text_actor:
            self.renderer.RemoveActor(self.text_actor)
            self.text_actor = None
        
        # 添加所有按键模型
        self.all_keycap_actors = []
        for model, pos in keycap_models:
            if model is not None:
                actor = self._cq_to_vtk_actor(model, color=(0.8, 0.8, 0.8))
                if actor:
                    actor.SetPosition(pos)
                    self.renderer.AddActor(actor)
                    self.all_keycap_actors.append(actor)
        
        # 添加所有文字模型
        self.all_text_actors = []
        for model, pos in text_models:
            if model is not None:
                actor = self._cq_to_vtk_actor(model, color=(1.0, 0.0, 0.0))
                if actor:
                    actor.SetPosition(pos)
                    self.renderer.AddActor(actor)
                    self.all_text_actors.append(actor)
        
        # 重置相机并渲染
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def clear_all_models(self):
        """清除所有批量模型"""
        for actor in self.all_keycap_actors:
            self.renderer.RemoveActor(actor)
        for actor in self.all_text_actors:
            self.renderer.RemoveActor(actor)
        self.all_keycap_actors = []
        self.all_text_actors = []
    
    def _cq_to_vtk_actor(self, cq_object: cq.Workplane, color: tuple = (1.0, 1.0, 1.0)) -> vtk.vtkActor:
        """
        将CadQuery对象转换为VTK Actor
        
        参数:
            cq_object: CadQuery Workplane对象
            color: RGB颜色元组 (0-1范围)
        
        返回:
            VTK Actor对象
        """
        try:
            import tempfile
            import os
            
            # 使用临时文件
            with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # 导出为STL文件
                cq.exporters.export(cq_object, tmp_path)
                
                # 从文件读取STL
                reader = vtk.vtkSTLReader()
                reader.SetFileName(tmp_path)
                reader.Update()
                
                # 创建mapper
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(reader.GetOutputPort())
                
                # 创建actor
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.GetProperty().SetColor(color)
                actor.GetProperty().SetSpecular(0.5)
                actor.GetProperty().SetSpecularPower(30)
                
                return actor
            finally:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
            
        except Exception as e:
            print(f"转换CadQuery对象到VTK时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def clear(self):
        """清除所有模型"""
        self.update_model(None, None)
    
    def add_origin_marker(self):
        """添加坐标原点标记"""
        # 创建一个小球体标记原点
        sphere_source = vtk.vtkSphereSource()
        sphere_source.SetRadius(0.5)
        sphere_source.SetCenter(0, 0, 0)
        sphere_source.SetPhiResolution(20)
        sphere_source.SetThetaResolution(20)
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere_source.GetOutputPort())
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1.0, 1.0, 0.0)  # 黄色
        actor.GetProperty().SetOpacity(0.7)
        
        self.renderer.AddActor(actor)
        self.origin_actor = actor
    
    def add_reference_planes(self):
        """添加三个基准面（XY, XZ, YZ平面）"""
        plane_size = 20.0  # 基准面大小
        
        # XY平面（Z=0）
        xy_plane = vtk.vtkPlaneSource()
        xy_plane.SetOrigin(-plane_size/2, -plane_size/2, 0)
        xy_plane.SetPoint1(plane_size/2, -plane_size/2, 0)
        xy_plane.SetPoint2(-plane_size/2, plane_size/2, 0)
        
        xy_mapper = vtk.vtkPolyDataMapper()
        xy_mapper.SetInputConnection(xy_plane.GetOutputPort())
        
        xy_actor = vtk.vtkActor()
        xy_actor.SetMapper(xy_mapper)
        xy_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 红色 - XY平面
        xy_actor.GetProperty().SetOpacity(0.2)
        xy_actor.GetProperty().SetRepresentationToWireframe()
        self.renderer.AddActor(xy_actor)
        self.xy_plane_actor = xy_actor
        
        # XZ平面（Y=0）
        xz_plane = vtk.vtkPlaneSource()
        xz_plane.SetOrigin(-plane_size/2, 0, -plane_size/2)
        xz_plane.SetPoint1(plane_size/2, 0, -plane_size/2)
        xz_plane.SetPoint2(-plane_size/2, 0, plane_size/2)
        
        xz_mapper = vtk.vtkPolyDataMapper()
        xz_mapper.SetInputConnection(xz_plane.GetOutputPort())
        
        xz_actor = vtk.vtkActor()
        xz_actor.SetMapper(xz_mapper)
        xz_actor.GetProperty().SetColor(0.0, 1.0, 0.0)  # 绿色 - XZ平面
        xz_actor.GetProperty().SetOpacity(0.2)
        xz_actor.GetProperty().SetRepresentationToWireframe()
        self.renderer.AddActor(xz_actor)
        self.xz_plane_actor = xz_actor
        
        # YZ平面（X=0）
        yz_plane = vtk.vtkPlaneSource()
        yz_plane.SetOrigin(0, -plane_size/2, -plane_size/2)
        yz_plane.SetPoint1(0, plane_size/2, -plane_size/2)
        yz_plane.SetPoint2(0, -plane_size/2, plane_size/2)
        
        yz_mapper = vtk.vtkPolyDataMapper()
        yz_mapper.SetInputConnection(yz_plane.GetOutputPort())
        
        yz_actor = vtk.vtkActor()
        yz_actor.SetMapper(yz_mapper)
        yz_actor.GetProperty().SetColor(0.0, 0.0, 1.0)  # 蓝色 - YZ平面
        yz_actor.GetProperty().SetOpacity(0.2)
        yz_actor.GetProperty().SetRepresentationToWireframe()
        self.renderer.AddActor(yz_actor)
        self.yz_plane_actor = yz_actor
    
    def reset_camera(self):
        """重置相机视角"""
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
