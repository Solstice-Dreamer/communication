import os
import time
import send_command
import numpy as np
WATCH_FOLDER = "./path"

# def read_txt_point(filepath):
#     matrixA = []
#     try:
#         with open(filepath, "r", encoding="utf-8") as f:
#             for line in f:
#                 line = line.strip()
#                 if line == "":
#                     continue
#                 # 判断首字母
#                 row = [float(x) for x in line.split()]
#                 matrixA.append(row)
#         print(f"读取文件成功：{filepath}")
#     except Exception as e:
#         print(f"读取文件失败：{filepath}, 错误信息：{e}")
#     return matrixA


def read_txt_point(filepath, check_interval=1.0):
    """
    持续检查并读取文件，直到文件存在并成功读取

    参数:
        filepath: 文件路径
        check_interval: 检查间隔时间(秒)
    """
    matrixA = []

    while True:
        try:
            # 先检查文件是否存在
            if not os.path.exists(filepath):
                print(f"文件 {filepath} 不存在，等待 {check_interval} 秒后重试...")
                time.sleep(check_interval)
                continue

            # 文件存在，尝试读取
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line == "":
                        continue
                    # 判断首字母
                    row = [float(x) for x in line.split()]
                    matrixA.append(row)

            print(f"读取文件成功：{filepath}")
            return matrixA

        except PermissionError:
            print(f"没有权限访问文件 {filepath}，等待 {check_interval} 秒后重试...")
            time.sleep(check_interval)
        except ValueError as ve:
            print(f"文件内容格式错误：{ve}，等待 {check_interval} 秒后重试...")
            time.sleep(check_interval)
            matrixA = []  # 清空之前读取的内容
        except Exception as e:
            print(f"读取文件 {filepath} 时发生未知错误：{e}，等待 {check_interval} 秒后重试...")
            time.sleep(check_interval)
            matrixA = []  # 清空之前读取的内容

def execute_back(alt):
    start_point = read_txt_point(os.path.join(WATCH_FOLDER, 'start_point.txt'))
    current_point = read_txt_point(os.path.join(WATCH_FOLDER, 'gps_point.txt'))
    path = np.zeros((3, 3))

    # 计算经过的三个点
    for i in range(3):
        path[0][i] = float(current_point[0][i])
        path[1][i] = float(start_point[0][i])
        path[2][i] = float(start_point[0][i])

    path[0][2] = path[0][2] + alt
    path[1][2] = path[1][2] + alt
    path[1][2] = path[1][2] + 2.0 # 防止因GPS不准而造成的碰撞

    # 若存在xml文件，读取，如果为return，则转化为三个点传给本机，同时写一个land指令
    try:
        point_num = path.shape[0]
        count = 0
        while True:
            if count == point_num:
                break
            with open(os.path.join(WATCH_FOLDER, 'reached.sign'), 'r', encoding='utf-8') as f:
                first_char = f.read(1)
                if first_char == "1":
                    send_command.flytopoint("127.0.0.1", path[count][0], path[count][1], path[count][2])
                    with open(os.path.join(WATCH_FOLDER, 'reached.sign'), 'w', encoding='utf-8') as f:
                        f.write("0")
                    count = count + 1
            time.sleep(1)  # 每秒检查一次

        send_command.land("127.0.0.1")
    except KeyboardInterrupt:
        print("\n程序终止。")

def execute_follow(follow_ip, alt):
    try:
        with open(os.path.join(WATCH_FOLDER, 'follow.sign'), 'w', encoding='utf-8') as f:
            f.write("1")
        ip_num = len(follow_ip)
        points = np.zeros((ip_num, 3))

        while True:
            # 若当前状态不为follow，则退出循环
            with open(os.path.join(WATCH_FOLDER, 'follow.sign'), 'r', encoding='utf-8') as f:
                first_char = f.read(1)
            if first_char == "0":
                break

            current_point = read_txt_point(os.path.join(WATCH_FOLDER, 'gps_point.txt'))
            for i in range(ip_num):
                for j in range(3):
                    points[i][j] = float(current_point[0][j])
                points[i][2] = points[i][2] - (i + 1) * alt

            for i in range(ip_num):
                send_command.flytopoint(follow_ip[i], points[i][0], points[i][1], points[i][2])

            time.sleep(3)  # 每3秒发送一次


    except KeyboardInterrupt:
        print("\n程序终止。")
