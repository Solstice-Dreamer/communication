import sys
import os
import math
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtCore import Qt, QPoint

TILE_SIZE = 256

def deg2num(lat_deg, lon_deg, zoom):
    """经纬度转瓦片号"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int(
        (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
        / 2.0
        * n
    )
    return xtile, ytile

class TileMapWidget(QWidget):
    def __init__(self, tile_dir, center_lat, center_lon, zoom, parent=None):
        super().__init__(parent)
        self.tile_dir = tile_dir
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom = zoom
        self.drag_pos = None
        self.offset_x = 0
        self.offset_y = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        n = 2 ** self.zoom  # 瓦片总数（宽和高都是n）

        # 根据当前offset_x/y，计算地图起点左上角瓦片的绘制偏移
        # 这里假设0,0瓦片绘制在(-offset_x, -offset_y)
        # offset_x, offset_y 表示地图视图相对于瓦片0,0的像素偏移

        for xtile in range(n):
            for ytile in range(n):
                tile_path = os.path.join(
                    self.tile_dir,
                    str(self.zoom),
                    str(xtile),
                    f"{ytile}.png",
                )
                if os.path.exists(tile_path):
                    pixmap = QPixmap(tile_path)
                    x_pix = xtile * TILE_SIZE - self.offset_x
                    y_pix = ytile * TILE_SIZE - self.offset_y

                    # 只绘制在窗口可见范围内的瓦片，略微优化性能
                    if (
                        x_pix + TILE_SIZE < 0
                        or x_pix > w
                        or y_pix + TILE_SIZE < 0
                        or y_pix > h
                    ):
                        continue

                    painter.drawPixmap(x_pix, y_pix, pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            delta = event.pos() - self.drag_pos
            self.offset_x -= delta.x()
            self.offset_y -= delta.y()
            self.drag_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 瓦片地图浏览器")
        self.resize(800, 600)  # 改大点窗口方便看

        tile_dir = "/home/seob007/communication/tiles"
        center_lat = 30.6
        center_lon = 114.3
        zoom = 14

        self.map_widget = TileMapWidget(tile_dir, center_lat, center_lon, zoom)
        self.setCentralWidget(self.map_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())