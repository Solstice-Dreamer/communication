# import numpy as np
# from PyQt6 import QtWidgets
# import pyqtgraph.opengl as gl
# from pyqtgraph.Qt import QtCore
# from triangle3D import Triangle3D
# import random
#
# class ColorGenerator:
#     def __init__(self):
#         self.used_colors = set()
#
#     def _color_to_tuple(self, color):
#         return tuple(round(c, 2) for c in color)
#
#     def get_unique_color(self):
#         max_attempts = 1000
#         for _ in range(max_attempts):
#             # 随机生成 RGBA (0~1 float)
#             color = (
#                 random.random(),  # R
#                 random.random(),  # G
#                 random.random(),  # B
#                 1.0               # A 不透明
#             )
#             color_tuple = self._color_to_tuple(color)
#             if color_tuple not in self.used_colors:
#                 self.used_colors.add(color_tuple)
#                 return color
#         raise RuntimeError("无法找到未使用的颜色（已用尽尝试次数）")
#
# class LegendWindow(QtWidgets.QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("无人机状态")
#         self.resize(200, 300)
#         self.layout = QtWidgets.QVBoxLayout(self)
#         self.entries = {}  # ip -> QWidget
#
#     def update_entry(self, ip, color, battery):
#         if ip in self.entries:
#             label = self.entries[ip]
#             label.setText(f"{ip} | 电量: {battery}%")
#         else:
#             # 新建条目
#             color_box = QtWidgets.QLabel()
#             color_box.setFixedSize(15, 15)
#             color_box.setStyleSheet(
#                 f"background-color: rgba({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}, {int(color[3]*255)});"
#             )
#
#             text = QtWidgets.QLabel(f"{ip} | 电量: {battery}%")
#             row = QtWidgets.QHBoxLayout()
#             row.addWidget(color_box)
#             row.addWidget(text)
#
#             container = QtWidgets.QWidget()
#             container.setLayout(row)
#             self.layout.addWidget(container)
#             self.entries[ip] = text  # 只更新 label 文本即可
#
#
# class UAVsingle(QtWidgets.QMainWindow):
#     def __init__(self, ip, color):
#         super().__init__()
#         self.ip = ip
#         self.color = color
#         self.view = None
#
#         self.position = np.empty((0, 3))  # 存三维坐标
#         self.direction = np.array([[0, 0, 1]])  # 存无人机飞行方向
#         self.theta = 0  # 存显示动画的旋转角
#         self.battery = 0  # 存电量
#
#         # 设置圆点和三角形
#         self.scatter = gl.GLScatterPlotItem(size=8.0, color=self.color)
#         self.scatter.setGLOptions('opaque')  # 强制使用不透明渲染
#         self.tri = None
#         self.tri_visible = True
#
#     def set_view(self, view):
#         self.view = view
#
#     def animate_tri(self, my_rad):
#         if self.tri is not None and self.view is not None:
#             # 令 roll 线性增加
#             self.theta += np.deg2rad(my_rad)  # 每次增加5度（弧度）
#             # 可选：让 theta 在[0,2π)区间循环
#             if self.theta > 2 * np.pi:
#                 self.theta -= 2 * np.pi
#             # 仅更新 roll，不改 direction
#             self.tri.set_roll(self.theta)
#
#     def update_data(self, new_position: np.ndarray, new_battery):
#         if self.view is None:
#             raise ValueError("请先设置显示界面")
#         if new_position.shape != (1, 3):
#             raise ValueError("UAV的坐标必须是1*3的数组")
#
#         self.position = np.vstack((self.position, new_position[0]))
#         self.battery = new_battery
#
#         # 更新散点：不显示最后一个点，只显示前面所有点
#         if len(self.position) > 1:
#             self.scatter.setData(pos=self.position[:-1], color=self.color)
#             new_direction = (self.position[-1] - self.position[-2]).reshape(1,3)
#             if np.linalg.norm(new_direction) > 0.05: # 如果前后位置差小于0.05,不更新方向
#                 self.direction = new_direction
#         else:
#             self.scatter.setData(pos=np.empty((0,3)), color=self.color)
#         self.view.addItem(self.scatter)
#         # 若三角形不存在，则添加，否则直接更新位置和姿态
#         if self.tri is None:
#             self.tri = Triangle3D(new_position[0], self.direction[0], length=0.3, width=0.2, color=self.color)
#             self.view.addItem(self.tri)
#         else:
#             self.tri.set_position(new_position[0])
#             self.tri.set_direction(self.direction[0])
#
# def create_closed_cylinder(radius=0.3, length=1.0, cols=32):
#     """
#     创建一个封顶封底、法线平滑、顶点不重复的圆柱体 MeshData。
#     圆柱沿 Z 轴方向，底部在 z=0，顶部在 z=length。
#     """
#     # 生成侧面网格：2 * cols 个点
#     angle = np.linspace(0, 2 * np.pi, cols, endpoint=False)
#     x = radius * np.cos(angle)
#     y = radius * np.sin(angle)
#     z_bottom = np.zeros(cols)
#     z_top = np.full(cols, length)
#
#     # 侧面顶点：交错排列 bottom, top, bottom, top ...
#     verts = []
#     for i in range(cols):
#         verts.append([x[i], y[i], z_bottom[i]])
#         verts.append([x[i], y[i], z_top[i]])
#     verts = np.array(verts, dtype=np.float32)
#
#     # 添加中心顶点
#     bottom_center = [0, 0, 0]
#     top_center = [0, 0, length]
#     bottom_center_idx = len(verts)
#     top_center_idx = len(verts) + 1
#     verts = np.vstack([verts, bottom_center, top_center])
#
#     # 侧面三角形
#     faces = []
#     for i in range(cols):
#         i0 = i * 2
#         i1 = i * 2 + 1
#         i2 = (i * 2 + 2) % (cols * 2)
#         i3 = (i * 2 + 3) % (cols * 2)
#         faces.append([i0, i2, i1])
#         faces.append([i2, i3, i1])
#
#     # 底面三角形
#     for i in range(cols):
#         i0 = i * 2
#         i1 = (i * 2 + 2) % (cols * 2)
#         faces.append([bottom_center_idx, i0, i1])
#
#     # 顶面三角形
#     for i in range(cols):
#         i0 = i * 2 + 1
#         i1 = (i * 2 + 3) % (cols * 2)
#         faces.append([top_center_idx, i1, i0])
#
#     faces = np.array(faces, dtype=np.int32)
#
#     return gl.MeshData(vertexes=verts, faces=faces)
#
# class UAVmonitor(QtWidgets.QMainWindow, ColorGenerator):
#     def __init__(self, computer_pos):
#         super().__init__()
#         self.setWindowTitle("UAV航迹监测平台")
#         self.resize(800, 800)
#         self.color_generator = ColorGenerator()
#
#         self.view = gl.GLViewWidget()
#         self.setCentralWidget(self.view)
#         self.view.opts['bgcolor'] = (0.7, 0.7, 0.7, 1.0)  # 0-1 float 格式也可
#         self.view.setCameraPosition(distance=40)
#
#         self.uavs = {}  # 存储多个 UAV 实例：{ip: UAVsingle}
#
#         self._add_axes()
#         self._add_grid()
#
#         self._add_localhost_model(position=np.array([0,0,0]))
#         # 新建图例窗口
#         self.legend = LegendWindow()
#         self.legend.show()
#
#         self.flash_timer = QtCore.QTimer()
#         self.flash_timer.timeout.connect(self.animate_all_tris)
#         self.flash_timer.start(500)
#
#     # 新增本机的表示
#     def _add_localhost_model(self, position: np.ndarray):
#         # 圆柱体代表本机
#         cyl_mesh = create_closed_cylinder(radius=0.3, length=1, cols=32)
#         cylinder = gl.GLMeshItem(meshdata=cyl_mesh, smooth=True, color=(1, 1, 0, 1), shader="shaded", drawFaces=True)
#         cylinder.translate(*position)
#         cylinder.translate(0, 0, -0.5)  # 提升圆柱使其底部与地面对齐
#         self.view.addItem(cylinder)
#
#
#     def animate_all_tris(self):
#         for uav in self.uavs.values():
#             uav.animate_tri(30)
#
#     def _add_axes(self):
#         axis_length = 10
#         axes = np.array([
#             [[0, 0, 0], [axis_length, 0, 0]],
#             [[0, 0, 0], [0, axis_length, 0]],
#             [[0, 0, 0], [0, 0, axis_length]]
#         ])
#         colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
#         for i in range(3):
#             axis = gl.GLLinePlotItem(pos=axes[i], color=colors[i], width=3, antialias=True)
#             self.view.addItem(axis)
#
#     def _add_grid(self):
#         size = 20  # 网格尺寸
#         step = 1
#         lines = []
#
#         for x in range(-size, size + 1, step):
#             lines.append([[x, -size, 0], [x, size, 0]])
#         for y in range(-size, size + 1, step):
#             lines.append([[-size, y, 0], [size, y, 0]])
#
#         lines = np.array(lines).reshape(-1, 3)
#         grid = gl.GLLinePlotItem(
#             pos=lines,
#             mode='lines',
#             color=(0, 0, 0, 1),  # 黑色
#             width=1,
#             antialias=True
#         )
#         self.view.addItem(grid)
#
#     def update_uav(self, ip, pos: np.ndarray, battery):
#         """更新某个 UAV 的位置和朝向, 如果没有就添加无人机"""
#         if ip in self.uavs:
#             self.uavs[ip].update_data(pos, battery)
#         else:
#             color = self.color_generator.get_unique_color()
#             self.uavs[ip] = UAVsingle(ip, color)
#             self.uavs[ip].set_view(self.view)
#             self.uavs[ip].update_data(pos, battery)
#         self.legend.update_entry(ip, self.uavs[ip].color, battery)



import numpy as np
from PyQt6 import QtWidgets
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore
from triangle3D import Triangle3D
import random

class ColorGenerator:
    def __init__(self):
        self.used_colors = set()

    def _color_to_tuple(self, color):
        return tuple(round(c, 2) for c in color)

    def get_unique_color(self):
        max_attempts = 1000
        for _ in range(max_attempts):
            color = (
                random.random(),
                random.random(),
                random.random(),
                1.0
            )
            color_tuple = self._color_to_tuple(color)
            if color_tuple not in self.used_colors:
                self.used_colors.add(color_tuple)
                return color
        # 超过尝试次数时返回默认颜色并警告
        print("警告：颜色池用尽，使用默认颜色")
        return (0.5, 0.5, 0.5, 1.0)

class LegendWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无人机状态")
        self.resize(200, 300)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.entries = {}

    def update_entry(self, ip, color, battery):
        try:
            if not (0 <= battery <= 100):
                battery = max(0, min(100, battery))
            if ip in self.entries:
                label = self.entries[ip]
                label.setText(f"{ip} | 电量: {battery}%")
            else:
                color_box = QtWidgets.QLabel()
                color_box.setFixedSize(15, 15)
                color_box.setStyleSheet(
                    f"background-color: rgba({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}, {int(color[3]*255)});"
                )
                text = QtWidgets.QLabel(f"{ip} | 电量: {battery}%")
                row = QtWidgets.QHBoxLayout()
                row.addWidget(color_box)
                row.addWidget(text)
                container = QtWidgets.QWidget()
                container.setLayout(row)
                self.layout.addWidget(container)
                self.entries[ip] = text
        except Exception as e:
            print(f"更新图例异常: {e}")

class UAVsingle(QtWidgets.QMainWindow):
    def __init__(self, ip, color):
        super().__init__()
        self.ip = ip
        self.color = color
        self.view = None

        self.position = np.empty((0, 3))
        self.direction = np.array([[0, 0, 1]])
        self.theta = 0
        self.battery = 0

        self.scatter = gl.GLScatterPlotItem(size=8.0, color=self.color)
        self.scatter.setGLOptions('opaque')
        self.tri = None
        self.tri_visible = True

    def set_view(self, view):
        self.view = view

    def animate_tri(self, my_rad):
        if self.tri is not None and self.view is not None:
            self.theta += np.deg2rad(my_rad)
            if self.theta > 2 * np.pi:
                self.theta -= 2 * np.pi
            self.tri.set_roll(self.theta)

    def update_data(self, new_position: np.ndarray, new_battery):
        if self.view is None:
            raise ValueError("请先设置显示界面")
        if new_position.shape != (1, 3):
            raise ValueError("UAV的坐标必须是1*3的数组")
        if not isinstance(new_battery, (int, float)):
            raise ValueError("battery 应为数字类型")
        if not (0 <= new_battery <= 100):
            print(f"警告: battery值 {new_battery} 超出合理范围 (0-100)，自动调整")
            new_battery = max(0, min(100, new_battery))

        self.position = np.vstack((self.position, new_position[0]))
        self.battery = new_battery

        if len(self.position) > 1:
            self.scatter.setData(pos=self.position[:-1], color=self.color)
            new_direction = (self.position[-1] - self.position[-2]).reshape(1,3)
            if np.linalg.norm(new_direction) > 0.05:
                self.direction = new_direction
        else:
            self.scatter.setData(pos=np.empty((0,3)), color=self.color)

        if self.view is not None:
            self.view.addItem(self.scatter)

        if self.tri is None:
            self.tri = Triangle3D(new_position[0], self.direction[0], length=0.3, width=0.2, color=self.color)
            self.view.addItem(self.tri)
        else:
            self.tri.set_position(new_position[0])
            self.tri.set_direction(self.direction[0])

def create_closed_cylinder(radius=0.3, length=1.0, cols=32):
    """
    创建一个封顶封底、法线平滑、顶点不重复的圆柱体 MeshData。
    圆柱沿 Z 轴方向，底部在 z=0，顶部在 z=length。
    """
    # 生成侧面网格：2 * cols 个点
    angle = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    x = radius * np.cos(angle)
    y = radius * np.sin(angle)
    z_bottom = np.zeros(cols)
    z_top = np.full(cols, length)

    # 侧面顶点：交错排列 bottom, top, bottom, top ...
    verts = []
    for i in range(cols):
        verts.append([x[i], y[i], z_bottom[i]])
        verts.append([x[i], y[i], z_top[i]])
    verts = np.array(verts, dtype=np.float32)

    # 添加中心顶点
    bottom_center = [0, 0, 0]
    top_center = [0, 0, length]
    bottom_center_idx = len(verts)
    top_center_idx = len(verts) + 1
    verts = np.vstack([verts, bottom_center, top_center])

    # 侧面三角形
    faces = []
    for i in range(cols):
        i0 = i * 2
        i1 = i * 2 + 1
        i2 = (i * 2 + 2) % (cols * 2)
        i3 = (i * 2 + 3) % (cols * 2)
        faces.append([i0, i2, i1])
        faces.append([i2, i3, i1])

    # 底面三角形
    for i in range(cols):
        i0 = i * 2
        i1 = (i * 2 + 2) % (cols * 2)
        faces.append([bottom_center_idx, i0, i1])

    # 顶面三角形
    for i in range(cols):
        i0 = i * 2 + 1
        i1 = (i * 2 + 3) % (cols * 2)
        faces.append([top_center_idx, i1, i0])

    faces = np.array(faces, dtype=np.int32)

    return gl.MeshData(vertexes=verts, faces=faces)


class UAVmonitor(QtWidgets.QMainWindow, ColorGenerator):
    def __init__(self, computer_pos):
        super().__init__()
        self.setWindowTitle("UAV航迹监测平台")
        self.resize(800, 800)
        self.color_generator = ColorGenerator()

        self.view = gl.GLViewWidget()
        self.setCentralWidget(self.view)
        self.view.opts['bgcolor'] = (0.7, 0.7, 0.7, 1.0)
        self.view.setCameraPosition(distance=40)

        self.uavs = {}

        self._add_axes()
        self._add_grid()
        self._add_localhost_model(position=np.array([0,0,0]))

        self.legend = LegendWindow()
        self.legend.show()

        self.flash_timer = QtCore.QTimer()
        self.flash_timer.timeout.connect(self.animate_all_tris)
        self.flash_timer.start(500)

    def _add_localhost_model(self, position: np.ndarray):
        cyl_mesh = create_closed_cylinder(radius=0.3, length=1, cols=32)
        cylinder = gl.GLMeshItem(meshdata=cyl_mesh, smooth=True, color=(1, 1, 0, 1), shader="shaded", drawFaces=True)
        cylinder.translate(*position)
        cylinder.translate(0, 0, -0.5)
        self.view.addItem(cylinder)

    def animate_all_tris(self):
        for uav in self.uavs.values():
            try:
                uav.animate_tri(30)
            except Exception as e:
                print(f"动画异常: {e}")

    def _add_axes(self):
        axis_length = 10
        axes = np.array([
            [[0, 0, 0], [axis_length, 0, 0]],
            [[0, 0, 0], [0, axis_length, 0]],
            [[0, 0, 0], [0, 0, axis_length]]
        ])
        colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
        for i in range(3):
            axis = gl.GLLinePlotItem(pos=axes[i], color=colors[i], width=3, antialias=True)
            self.view.addItem(axis)

    def _add_grid(self):
        size = 20  # 网格尺寸
        step = 1
        lines = []

        for x in range(-size, size + 1, step):
            lines.append([[x, -size, 0], [x, size, 0]])
        for y in range(-size, size + 1, step):
            lines.append([[-size, y, 0], [size, y, 0]])

        lines = np.array(lines).reshape(-1, 3)
        grid = gl.GLLinePlotItem(
            pos=lines,
            mode='lines',
            color=(0, 0, 0, 1),  # 黑色
            width=1,
            antialias=True
        )
        self.view.addItem(grid)

    def update_uav(self, ip, pos: np.ndarray, battery):
        try:
            if ip in self.uavs:
                self.uavs[ip].update_data(pos, battery)
            else:
                color = self.color_generator.get_unique_color()
                self.uavs[ip] = UAVsingle(ip, color)
                self.uavs[ip].set_view(self.view)
                self.uavs[ip].update_data(pos, battery)
            self.legend.update_entry(ip, self.uavs[ip].color, battery)
        except Exception as e:
            print(f"更新无人机数据异常: {e}")

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = UAVmonitor()
#     # window = ThreeDScatter("192.168.1.1", (1, 1, 0, 1))
#     window.show()
#
#     import math
#     def quat_from_axis_angle(axis, angle_rad):
#         axis = axis / np.linalg.norm(axis)
#         w = math.cos(angle_rad / 2)
#         x, y, z = axis * math.sin(angle_rad / 2)
#         return np.array([w, x, y, z])
#
#     def send_points(i=0, max_i=20):
#         if i >= max_i:
#             return
#         pos = np.array([[i, i, i]])
#         pos2 = np.array([[i, -i, i]])
#         angle = i * (2*math.pi / max_i)
#         quat = quat_from_axis_angle(np.array([0, 1, 0]), angle)
#         quat2 = quat_from_axis_angle(np.array([1, 0, 0]), angle)
#         window.update_uav("192.168.1.1", pos, quat.reshape(1,4))
#         window.update_uav("192.168.1.2", pos2, quat2.reshape(1, 4))
#         QtCore.QTimer.singleShot(500, lambda: send_points(i+1, max_i))
#
#     send_points()
#
#     sys.exit(app.exec())


# import sys
# import numpy as np
# from PyQt6 import QtWidgets
# import pyqtgraph.opengl as gl
# from pyqtgraph.Qt import QtCore
# from cone3D import Cone3D
# import random
#
# class ColorGenerator:
#     def __init__(self):
#         self.used_colors = set()
#
#     def _color_to_tuple(self, color):
#         return tuple(round(c, 2) for c in color)
#
#     def get_unique_color(self):
#         max_attempts = 1000
#         for _ in range(max_attempts):
#             # 随机生成 RGBA (0~1 float)
#             color = (
#                 random.random(),  # R
#                 random.random(),  # G
#                 random.random(),  # B
#                 1.0               # A 不透明
#             )
#             color_tuple = self._color_to_tuple(color)
#             if color_tuple not in self.used_colors:
#                 self.used_colors.add(color_tuple)
#                 return color
#         raise RuntimeError("无法找到未使用的颜色（已用尽尝试次数）")
#
# class LegendWindow(QtWidgets.QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("无人机状态")
#         self.resize(200, 300)
#         self.layout = QtWidgets.QVBoxLayout(self)
#         self.entries = {}  # ip -> QWidget
#
#     def update_entry(self, ip, color, battery):
#         if ip in self.entries:
#             label = self.entries[ip]
#             label.setText(f"{ip} | 电量: {battery}%")
#         else:
#             # 新建条目
#             color_box = QtWidgets.QLabel()
#             color_box.setFixedSize(15, 15)
#             color_box.setStyleSheet(
#                 f"background-color: rgba({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}, {int(color[3]*255)});"
#             )
#
#             text = QtWidgets.QLabel(f"{ip} | 电量: {battery}%")
#             row = QtWidgets.QHBoxLayout()
#             row.addWidget(color_box)
#             row.addWidget(text)
#
#             container = QtWidgets.QWidget()
#             container.setLayout(row)
#             self.layout.addWidget(container)
#             self.entries[ip] = text  # 只更新 label 文本即可
#
#
# class UAVsingle(QtWidgets.QMainWindow):
#     def __init__(self, ip, color):
#         super().__init__()
#         self.ip = ip
#         self.color = color
#         self.view = None
#
#         self.position = np.empty((0, 3))  # 存三维坐标
#         self.directions = np.empty((0, 4))  # 存四元数
#         self.battery = np.empty((0, 1))  # 存电量
#
#         # 设置圆点和圆锥
#         self.scatter = gl.GLScatterPlotItem(size=8.0, color=self.color)
#         self.scatter.setGLOptions('opaque')  # 强制使用不透明渲染
#         self.cone = None
#         self.cone_visible = True
#
#         # # 定时器控制圆锥闪烁
#         # self.flash_timer = QtCore.QTimer()
#         # self.flash_timer.timeout.connect(self.toggle_cone_visibility)
#         # self.flash_timer.start(1000)  # 每1000ms切换一次
#
#     def set_view(self, view):
#         self.view = view
#
#     def toggle_cone_visibility(self):
#         if self.cone is not None and self.view is not None:
#             if self.cone_visible:
#                 self.view.removeItem(self.cone)
#                 self.cone_visible = False
#             else:
#                 self.view.addItem(self.cone)
#                 self.cone_visible = True
#
#     def update_data(self, new_position: np.ndarray, new_quaternion: np.ndarray, new_battery: np.ndarray):
#         if self.view is None:
#             raise ValueError("请先设置显示界面")
#         if new_position.shape != (1, 3):
#             raise ValueError("UAV的坐标必须是1*3的数组")
#         if new_quaternion.shape != (1, 4):
#             raise ValueError("UAV的四元数必须是1*4的数组")
#         if new_battery.shape != (1, 1):
#             raise ValueError("UAV的电量必须是1*1的数组")
#
#         self.position = np.vstack((self.position, new_position[0]))
#         self.directions = np.vstack((self.directions, new_quaternion[0]))
#         self.battery = np.vstack((self.battery, new_battery[0]))
#
#         # 更新散点：不显示最后一个点，只显示前面所有点
#         #color_array = np.tile(np.array(self.color, dtype=np.float32), (len(self.position[:-1]), 1))
#         if len(self.position) > 1:
#             #self.scatter.setData(pos=self.position[:-1], color=color_array)
#             self.scatter.setData(pos=self.position[:-1], color=self.color)
#         else:
#             self.scatter.setData(pos=np.empty((0,3)), color=self.color)
#         self.view.addItem(self.scatter)
#         # 删除旧箭头
#         if self.cone is not None:
#             if self.cone_visible:
#                 self.view.removeItem(self.cone)
#             self.cone = None
#
#         self.cone = Cone3D(new_position[0], new_quaternion[0], radius=0.3, height=0.5, color=self.color)
#         # 圆锥位置与朝向
#         self.view.addItem(self.cone)
#         self.cone_visible = True
#
#
# class UAVmonitor(QtWidgets.QMainWindow, ColorGenerator):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("UAV航迹监测平台")
#         self.resize(800, 800)
#         self.color_generator = ColorGenerator()
#
#         self.view = gl.GLViewWidget()
#         self.setCentralWidget(self.view)
#         self.view.opts['bgcolor'] = (0.7, 0.7, 0.7, 1.0)  # 0-1 float 格式也可
#         # self.view.setBackgroundColor((0.7, 0.7, 0.7, 1.0))  # 设置背景为白色
#         self.view.setCameraPosition(distance=40)
#
#         self.uavs = {}  # 存储多个 UAV 实例：{ip: UAVsingle}
#
#         self._add_axes()
#         self._add_grid()
#
#         # 新建图例窗口
#         self.legend = LegendWindow()
#         self.legend.show()
#
#         self.flash_timer = QtCore.QTimer()
#         self.flash_timer.timeout.connect(self.toggle_all_cones)
#         self.flash_timer.start(1000)
#
#
#     def toggle_all_cones(self):
#         for uav in self.uavs.values():
#             uav.toggle_cone_visibility()
#
#     def _add_axes(self):
#         axis_length = 10
#         axes = np.array([
#             [[0, 0, 0], [axis_length, 0, 0]],
#             [[0, 0, 0], [0, axis_length, 0]],
#             [[0, 0, 0], [0, 0, -axis_length]]
#         ])
#         colors = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)]
#         for i in range(3):
#             axis = gl.GLLinePlotItem(pos=axes[i], color=colors[i], width=3, antialias=True)
#             self.view.addItem(axis)
#
#     # def _add_grid(self):
#     #     grid = gl.GLGridItem()
#     #     grid.scale(2, 2, 1)
#     #     self.view.addItem(grid)
#
#     def _add_grid(self):
#         size = 20  # 网格尺寸
#         step = 1
#         lines = []
#
#         for x in range(-size, size + 1, step):
#             lines.append([[x, -size, 0], [x, size, 0]])
#         for y in range(-size, size + 1, step):
#             lines.append([[-size, y, 0], [size, y, 0]])
#
#         lines = np.array(lines).reshape(-1, 3)
#         grid = gl.GLLinePlotItem(
#             pos=lines,
#             mode='lines',
#             color=(0, 0, 0, 1),  # 黑色
#             width=1,
#             antialias=True
#         )
#         self.view.addItem(grid)
#
#     def update_uav(self, ip, pos: np.ndarray, quat: np.ndarray, battery: np.ndarray):
#         """更新某个 UAV 的位置和朝向, 如果没有就添加无人机"""
#         if ip in self.uavs:
#             self.uavs[ip].update_data(pos, quat, battery)
#         else:
#             color = self.color_generator.get_unique_color()
#             self.uavs[ip] = UAVsingle(ip, color)
#             self.uavs[ip].set_view(self.view)
#             self.uavs[ip].update_data(pos, quat, battery)
#         self.legend.update_entry(ip, self.uavs[ip].color, float(battery[0, 0]))
#
#
#
#
# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = UAVmonitor()
#     # window = ThreeDScatter("192.168.1.1", (1, 1, 0, 1))
#     window.show()
#
#     import math
#     def quat_from_axis_angle(axis, angle_rad):
#         axis = axis / np.linalg.norm(axis)
#         w = math.cos(angle_rad / 2)
#         x, y, z = axis * math.sin(angle_rad / 2)
#         return np.array([w, x, y, z])
#
#     def send_points(i=0, max_i=20):
#         if i >= max_i:
#             return
#         pos = np.array([[i, i, i]])
#         pos2 = np.array([[i, -i, i]])
#         angle = i * (2*math.pi / max_i)
#         quat = quat_from_axis_angle(np.array([0, 1, 0]), angle)
#         quat2 = quat_from_axis_angle(np.array([1, 0, 0]), angle)
#         window.update_uav("192.168.1.1", pos, quat.reshape(1,4))
#         window.update_uav("192.168.1.2", pos2, quat.reshape(1, 4))
#         QtCore.QTimer.singleShot(500, lambda: send_points(i+1, max_i))
#
#     send_points()
#
#     sys.exit(app.exec())