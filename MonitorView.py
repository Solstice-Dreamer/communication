from PyQt6.QtCore import QUrl, QObject, pyqtSlot, Qt, pyqtSignal, QPointF
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QHBoxLayout
from PyQt6 import QtCore
from Icon import ColorGenerator, Cylinder3D
from UAV import UAV_3D, UAV_2D
import numpy as np
import pyqtgraph.opengl as gl
import json
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from UAV_flight import generate_uav_flight_plan
from pyproj import Transformer

# 图例窗口，用于显示无人机的电量等信息
class LegendWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无人机状态")
        self.resize(200, 300)
        self.layout = QVBoxLayout(self)
        self.entries = {}

    def update_entry(self, ip, color, battery):
        try:
            if not (0 <= battery <= 100):
                battery = max(0, min(100, battery))
            if ip in self.entries:
                label = self.entries[ip]
                label.setText(f"{ip} | 电量: {battery}%")
            else:
                color_box = QLabel()
                color_box.setFixedSize(15, 15)
                color_box.setStyleSheet(
                    f"background-color: rgba({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}, {int(color[3]*255)});"
                )
                text = QLabel(f"{ip} | 电量: {battery}%")
                row = QHBoxLayout()
                row.addWidget(color_box)
                row.addWidget(text)
                container = QWidget()
                container.setLayout(row)
                self.layout.addWidget(container)
                self.entries[ip] = text
        except Exception as e:
            print(f"更新图例异常: {e}")

class CoordinateTransformer2D:
    def __init__(self, screen_height, screen_width):
        self.corners = None
        self.screen_width = screen_width
        self.screen_height = screen_height

    def lonlat_to_screen(self, lon, lat):
        if self.corners is None:
            raise ValueError("还未获取地图角点坐标")
        left_lng = self.corners['topLeft'][0]
        right_lng = self.corners['topRight'][0]
        top_lat = self.corners['topLeft'][1]
        bottom_lat = self.corners['bottomLeft'][1]

        lng_span = right_lng - left_lng
        lat_span = top_lat - bottom_lat
        # if abs(lng_span) < 1e-10 or abs(lat_span) < 1e-10:
        #     return None
        #
        # if not (min(left_lng, right_lng) <= lon <= max(left_lng, right_lng)):
        #     return None
        # if not (min(bottom_lat, top_lat) <= lat <= max(bottom_lat, top_lat)):
        #     return None

        x_ratio = (lon - left_lng) / lng_span
        y_ratio = (top_lat - lat) / lat_span

        x_px = x_ratio * self.screen_width
        y_px = y_ratio * self.screen_height

        return x_px, y_px


# 无人机三维地图显示类
class UAVmonitor_3D(QMainWindow, ColorGenerator):
    def __init__(self, computer_pos):
        super().__init__()
        self.setWindowTitle("UAV三维航迹监测平台")
        self.resize(800, 800)
        self.color_generator = ColorGenerator() # 为统一二维三维的可视化的颜色，在main函数里定义color_generator，这里的不用

        self.view = gl.GLViewWidget()
        self.setCentralWidget(self.view)
        self.view.opts['bgcolor'] = (0.7, 0.7, 0.7, 1.0)
        self.view.setCameraPosition(distance=40)
        self.computer_pos = computer_pos
 
        self.uavs = {}

        self._add_axes()
        self._add_grid()
        self._add_ground_control()

        self.legend = LegendWindow()
        self.legend.show()

        self.flash_timer = QtCore.QTimer()
        self.flash_timer.timeout.connect(self.animate_all_tris)
        self.flash_timer.start(500)

        # 预先初始化转换器
        self.transformer = self.wgs84_to_local_transformer()

    def wgs84_to_local_transformer(self):
        """
        根据计算机的经度，确定所在的坐标系并返回转换器对象
        """
        center_lon = self.computer_pos[1]
        zone = int((center_lon - 1.5) / 3) + 1
        epsg_code = 4509 + zone
        transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg_code}", always_xy=True)
        return transformer

    def wgs84_to_local_coordinates(self, position):
        try:
            x0, y0 = self.transformer.transform(self.computer_pos[1], self.computer_pos[0])
            x, y = self.transformer.transform(position[0][1], position[0][0])  # 使用预先初始化的 transformer(先经度，后纬度)
            return np.array([x - x0, y - y0, position[0][2]]).reshape(1, 3)  # 返回本地坐标
        except ValueError as e:
            print(f"坐标转换失败：{e}")
        except Exception as e:
            print(f"未知错误：{e}")
        return None

    # 添加地面站
    def _add_ground_control(self):
        cylinder = Cylinder3D([0, 0, 0])
        self.view.addItem(cylinder)

    # 添加坐标轴
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

    # 添加网格
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

    # 为无人机三角形添加动画
    def animate_all_tris(self):
        for uav in self.uavs.values():
            try:
                uav.animate_tri(30)
            except Exception as e:
                print(f"动画异常: {e}")

    # 更新无人机信息
    def update_uav(self, ip, color=None, position=None, q=None, battery=-1):
        try:
            print(self.wgs84_to_local_coordinates(position))
            if ip in self.uavs:
                self.uavs[ip].update_data(self.wgs84_to_local_coordinates(position), q, battery)
            else:
                if color is None:
                    color = self.color_generator.get_unique_color()
                self.uavs[ip] = UAV_3D(ip, color)
                self.uavs[ip].set_view(self.view)
                self.uavs[ip].update_data(self.wgs84_to_local_coordinates(position), q, battery)
            self.legend.update_entry(ip, self.uavs[ip].color, battery)
        except Exception as e:
            print(f"更新无人机数据异常: {e}")

# 定义python与js通信的bridge类
class Bridge(QObject):
    polygonDrawn = pyqtSignal(str)  # 定义一个信号，参数是字符串
    mapInit = pyqtSignal(float, float, int)
    # logMessage = pyqtSignal(str)

    def __init__(self, uav_monitor2d_window):
        super().__init__()
        self.main_window = uav_monitor2d_window

    @pyqtSlot("QVariant")
    def onCornersChanged(self, coords):
        """
        接收来自 JS 的角点坐标
        """
        print("地图角点经纬度已更新：", coords)
        self.main_window.overlay.transformer.corners = coords

        # 通知 overlay 重绘
        if hasattr(self.main_window, "overlay"):
            self.main_window.overlay.update()

    @pyqtSlot(str)
    def onPolygonDrawn(self, geojson_str):
        print("收到来自 JS 的多边形数据：")
        self.polygonDrawn.emit(geojson_str)
        # 这里可以把 geojson 保存到文件，或者其他业务逻辑

    @pyqtSlot(float, float, int)
    def initMap(self, lat, lng, zoom):
        # 这里发送中心点和缩放
        self.mapInit.emit(lat, lng, zoom)
        print("已发送中心点和缩放层级的初值")

    # @pyqtSlot(str)
    # def onLogMessage(self, msg):
    #     print("JS调试日志：", msg)
    #     self.logMessage.emit(msg)

# OverlayWidget 管理所有 UAV
class OverlayWidget(QWidget):
    def __init__(self, parent=None, transformer=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.color_generator = ColorGenerator()
        self.uavs = {}          # ip → UAV_2D
        self.transformer = transformer
        self.plan_path = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 透明背景
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)

        # 依次绘制每一个 UAV
        for uav in self.uavs.values():
            uav.draw(painter)

        if self.plan_path:
            self.drawPlanPath(painter)

    def update_uav(self, ip, color=None, position=None, q=None, battery=-1):
        """
        外部调用：更新无人机数据并重绘。
        """
        try:
            if ip in self.uavs:
                self.uavs[ip].update_data(position, q, battery)
            else:
                if color is None:
                    color = self.color_generator.get_unique_color()
                self.uavs[ip] = UAV_2D(ip, color, self.transformer)
                self.uavs[ip].update_data(position, q, battery)
        except Exception as e:
            print(f"更新无人机数据异常: {e}")

        # 重绘 overlay
        self.update()

    def setPlanPathCoords(self, coords):
        self.plan_path = coords
        self.update()

    def drawPlanPath(self, painter):
        pen = QPen(Qt.GlobalColor.blue, 2)
        brush = QBrush(Qt.GlobalColor.red)
        painter.setPen(pen)

        points = []
        for lon, lat in self.plan_path:
            result = self.transformer.lonlat_to_screen(lon, lat)
            # if result is None:
            #     continue
            px, py = result
            points.append(QPointF(px, py))

        if len(points) >= 2:
            pen = QPen(QColor(255, 0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawPolyline(*points)

        radius = 6
        painter.setBrush(brush)
        for pt in points:
            painter.drawEllipse(pt, radius, radius)

        # print("轨迹绘制完成")

# 无人机二维地图显示类
class UAVmonitor_2D(QMainWindow, ColorGenerator):
    def __init__(self, width, height, ground_station, map_center_init, map_url):
        super().__init__()
        self.screen_width = width
        self.screen_height = height
        self.setWindowTitle("UAV二维航迹监测平台")
        self.resize(self.screen_width, self.screen_height)
        self.polygon_count = 0
        self.ground_station = ground_station
        self.map_center_init = map_center_init

        # 创建控件基类对象，并放入主窗口的中心
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # 启动布局管理工具，可以让地图自动随窗口缩放（布局放置在主窗口中心是因为传入了central_widget对象）
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        # 创建WebView对象
        self.webview = QWebEngineView()

        # 创建 Bridge 对象
        self.bridge = Bridge(self)


        # 创建并注册 WebChannel
        self.channel = QWebChannel()
        self.channel.registerObject('pyBridge', self.bridge)   # 必须先注册pyBridge
        self.webview.page().setWebChannel(self.channel)
        self.webview.loadFinished.connect(self.on_webview_loaded)
        # self.bridge.logMessage.connect(self.handleLog)

        # 设置 HTML URL
        self.webview.load(QUrl(map_url))
        # 页面加载完成后，通知 JS

        self.bridge.polygonDrawn.connect(self.handlePolygonDrawn)  # 连接信号
        # 将WebView对象放入布局管理工具中
        layout.addWidget(self.webview)

        # 设置转换函数
        transformer = CoordinateTransformer2D(self.screen_height, self.screen_width)
        # overlay 作为 webview 的子控件， 使其覆盖在地图上
        self.overlay = OverlayWidget(parent=self.webview, transformer=transformer)
        self.overlay.resize(self.webview.size())
        self.overlay.show()
        self.view = gl.GLViewWidget()
        # 同步 overlay 大小
        self.webview.resizeEvent = self.on_resize

    def on_resize(self, event):
        self.overlay.resize(self.webview.size())
        event.accept()

    # def on_webview_loaded(self):
    #     print("网页加载完成，开始初始化地图中心点")
    #     self.bridge.initMap(self.map_center_init[0], self.map_center_init[1], self.map_center_init[2])

    def on_webview_loaded(self):
        print("网页加载完成，准备延迟初始化地图中心点")
        QtCore.QTimer.singleShot(300, lambda: self.bridge.initMap(
            self.map_center_init[0], self.map_center_init[1], self.map_center_init[2]
        ))

    # def handleLog(self):
    #     print("yes")

    def handlePolygonDrawn(self, geojson_str):
        print("收到多边形数据，准备生成航迹")
        params = {
            'altitude': 1000,  # 飞行高度
            # 'vfov_deg': 14.34,     # 垂直视场角 °
            # 'hfov_deg': 21.46,     # 水平视场角 °
            'vfov_deg': 90.34,  # 垂直视场角 °
            'hfov_deg': 120.46,  # 水平视场角 °
            'speed': 8,  # 飞行速度 m/s
            'overlap_front': 0.8,  # 航向重叠度
            'overlap_side': 0.6,  # 旁向重叠度
            'ground_station': tuple(self.ground_station),  # 地面站位置
            'turn_time_buffer': 3.0,  # 转弯的冗余时间 s
        }
        try:
            # 如果需要先把字符串转成Python字典（验证格式），可以用json.loads
            geojson_obj = json.loads(geojson_str)
            # 提取 Polygon 第一个环的坐标
            coords_list = geojson_obj['geometry']['coordinates'][0]
            # 转成元组列表
            coords_tuples = [tuple(coord) for coord in coords_list]
            plan = generate_uav_flight_plan(coords_tuples, **params)
            plan_wgs84 = plan['wgs84_xyz_time']
            self.overlay.setPlanPathCoords( [t[:2] for t in plan_wgs84])

            self.polygon_count += 1
            save_path = f"polygon_path_{self.polygon_count}.txt"
            with open(save_path, "w", encoding="utf-8") as f:
                for lon, lat, z, t in plan['wgs84_xyz_time']:
                    f.write(f"{lon:.8f},{lat:.8f},{z:.6f},{t:.6f}\n")

        except json.JSONDecodeError as e:
            print("GeoJSON格式错误:", e)
            return


