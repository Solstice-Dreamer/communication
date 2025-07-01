from UAV import UAVmonitor
from pyqtgraph.Qt import QtCore
import sys
import socket
import numpy as np
import select
from PyQt6 import QtWidgets, QtCore
import argparse

LISTEN_IP = "0.0.0.0"

def monitoring(port=10001):
    print(f"监听UDP端口 {port} 中...（Ctrl+C 可退出）")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((LISTEN_IP, port))
        sock.setblocking(False)  # 设置为非阻塞
    except OSError as e:
        print(f"端口 {port} 无法绑定（可能已被占用）：{e}")
        sys.exit(1)

    app = QtWidgets.QApplication(sys.argv)
    computer_pos = [0, 0, 0]
    window = UAVmonitor(computer_pos)
    window.show()

    def check_udp_data():
        # 使用 select 检查是否有可读数据
        readable, _, _ = select.select([sock], [], [], 0)
        if readable:
            try:
                data, addr = sock.recvfrom(4096)
                message = data.decode().split()
                if message[0] == "state":
                    print(f"收到状态消息，来自无人机 {addr}")
                    pos = np.array([float(message[1]), float(message[2]), -float(message[3])]).reshape(1, 3)
                    quat = np.array([float(message[4]), float(message[5]), float(message[6]), float(message[7])]).reshape(1, 4)
                    battery = float(message[8])
                    window.update_uav(addr[0], pos, battery)
                # 可添加其他消息类型处理
            except Exception as e:
                print(f"解析异常: {e}")

    # 每隔50毫秒检查一次是否有UDP数据
    timer = QtCore.QTimer()
    timer.timeout.connect(check_udp_data)
    timer.start(50)

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n接收器已退出")
    finally:
        sock.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="程序运行指令")
    parser.add_argument("--port", type=int, default=10001, help="监听UDP端口，默认10001")
    args = parser.parse_args()

    monitoring(args.port)
