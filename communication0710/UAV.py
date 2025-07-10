# 无人机基类及二维三维可视化类
import numpy as np
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QPen, QFont

from Icon import Triangle3D, Line3D

# 无人机类
class UAV_base:
    def __init__(self, ip, color):
        # 无人机初始状态：坐标位置为空，飞行方向默认指向z轴正方向，姿态默认指向z轴正方向，电量为0
        self.ip = ip
        self.color = color
        self.position = np.empty((0, 3))
        self.path = np.empty((0, 3))
        self.direction = np.array([[0, 0, 1]])
        self.q = np.array([[1, 0, 0, 0]])
        self.battery = 0

    def update_position(self, new_position: np.ndarray):
        if new_position.shape != (1, 3):
            raise ValueError("UAV的坐标必须是1*3的数组")
        self.position = new_position
        self.path = np.vstack((self.path, new_position[0]))
        if self.path.shape[0] > 1:
            self.direction = (self.path[-1] - self.path[-2]).reshape(1,3)

    def update_q(self, new_q: np.ndarray):
        if new_q.shape != (1, 4):
            raise ValueError("UAV的姿态必须是1*4的数组")
        self.q = new_q

    def update_battery(self, new_battery):
        if not isinstance(new_battery, (int, float)):
            raise ValueError("battery 应为数字类型")
        if not (0 <= new_battery <= 100):
            print(f"警告: battery值 {new_battery} 超出合理范围 (0-100)，自动调整")
            new_battery = max(0, min(100, new_battery))
        self.battery = new_battery

class UAV_3D(UAV_base):
    def __init__(self, ip, color):
        super().__init__(ip=ip, color=color)
        self.view = None
        self.theta = 0
        self.tri = None
        self.line = []
        self.tri_visible = True

    # 设置界面
    def set_view(self, view):
        self.view = view

    # 设置无人机三角形动态转动速度
    def animate_tri(self, my_rad):
        if self.tri is not None and self.view is not None:
            self.theta += np.deg2rad(my_rad)
            if self.theta > 2 * np.pi:
                self.theta -= 2 * np.pi
            self.tri.set_roll(self.theta)

    # 更新三维地图
    def update_data(self, new_position: np.ndarray, new_q: np.ndarray, new_battery):
        if self.view is None:
            raise ValueError("请先设置显示界面")
        if new_position is not None:
            self.update_position(new_position)
        else:
            print(f"未接收到无人机{self.ip}的位置信息，不进行更新")
        if new_q is not None:
            self.update_q(new_q)
        else:
            print(f"未接收到无人机{self.ip}的姿态信息，不进行更新")
        if new_battery != -1:
            self.update_battery(new_battery)
        else:
            print(f"未接收到无人机{self.ip}的电量信息，不进行更新")

        if self.path.shape[0] > 1:
            line = Line3D(self.path[-2], self.path[-1], color=self.color, radius=0.01)
            if self.view is not None:
                self.view.addItem(line)
                self.line = [self.line, line]

        if self.tri is None:
            self.tri = Triangle3D(new_position[0], self.direction[0], length=0.3, width=0.2, color=self.color)
            self.view.addItem(self.tri)
        else:
            self.tri.set_position(new_position[0])
            self.tri.set_direction(self.direction[0])

# 单个 UAV 的绘制逻辑
class UAV_2D(UAV_base):
    def __init__(self, ip, color, transformer):
        super().__init__(ip=ip, color=color)
        self.transformer = transformer

    def update_data(self, new_position: np.ndarray, new_q: np.ndarray, new_battery):
        if new_position is not None:
            self.update_position(new_position)
        else:
            print(f"未接收到无人机{self.ip}的位置信息，不进行更新")
        if new_q is not None:
            self.update_q(new_q)
        else:
            print(f"未接收到无人机{self.ip}的姿态信息，不进行更新")
        if new_battery != -1:
            self.update_battery(new_battery)
        else:
            print(f"未接收到无人机{self.ip}的电量信息，不进行更新")

    def draw(self, painter):
        if self.position is None or len(self.position) == 0:
            return

        lon, lat = self.position[0][0], self.position[0][1]
        result = self.transformer.lonlat_to_screen(lon, lat)
        if result is None:
            return  # 不在屏幕内，跳过
        x, y = result

        color_255 = tuple(int(c * 255) for c in self.color)
        if len(color_255) == 4:
            r, g, b, _ = color_255
        else:
            r, g, b = color_255
        alpha = 180

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(r, g, b, alpha))
        painter.drawEllipse(int(x) - 10, int(y) - 10, 20, 20)

        painter.setPen(QPen(QColor(r, g, b)))
        painter.setFont(QFont("Arial", 12))
        painter.drawText(int(x) + 12, int(y), f"{self.ip}")

        # 画轨迹
        if self.path.shape[0] >= 2:
            points = []
            for lon, lat, _ in self.path:
                result = self.transformer.lonlat_to_screen(lon, lat)
                if result is None:
                    continue
                px, py = result
                points.append(QPointF(px, py))

            if len(points) >= 2:
                pen = QPen(QColor(r, g, b, alpha))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawPolyline(*points)




# class UAV_2D(UAV_base):
#     def __init__(self, ip, color, transformer):
#         super().__init__(ip=ip, color=color)
#         self.view = None
#         self.circle = None
#         self.line = []
#         self.circle_visible = True
#         self.transformer = transformer   # 坐标转换器
#
#     # 设置界面
#     def set_view(self, view):
#         self.view = view
#
#     # 更新二维地图
#     def update_data(self, new_position: np.ndarray, new_q: np.ndarray, new_battery):
#         # 更新无人机内部参数
#         if self.view is None:
#             raise ValueError("请先设置显示界面")
#         if new_position is not None:
#             self.update_position(new_position)
#         else:
#             print(f"未接收到无人机{self.ip}的位置信息，不进行更新")
#         if new_q is not None:
#             self.update_q(new_q)
#         else:
#             print(f"未接收到无人机{self.ip}的姿态信息，不进行更新")
#         if new_battery != -1:
#             self.update_battery(new_battery)
#         else:
#             print(f"未接收到无人机{self.ip}的电量信息，不进行更新")
#
#         # 更新绘图
#         if self.transformer is None:
#             x = new_position[0][0]
#             y = new_position[0][1]
#         else:
#             x, y = self.transformer.lonlat_to_screen(new_position[0][0], new_position[0][1])
#         # if self.path.shape[0] > 1:
#         #     line = Line2D(self.path[-2][:2], self.path[-1][:2], color=self.color, radius=0.01)
#         #     if self.view is not None:
#         #         self.view.addItem(line)
#         #         self.line = [self.line, line]
#         #
#         # if self.circle is None:
#         #     self.circle = Circle2D([x, y], radius=0.2, color=self.color)
#         #     self.view.addItem(self.circle)
#         # else:
#         #     self.circle.set_position([x, y])



