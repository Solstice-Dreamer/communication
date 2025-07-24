import socket
import json
import shlex
import argparse
from dataclasses import dataclass, asdict
import sys
import select
import time
import math


@dataclass
class Command:
    name: str
    params: dict = None

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))

def build_command_parser():
    parser = argparse.ArgumentParser(description="指令解析器")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # takeoff 子命令
    takeoff_parser = subparsers.add_parser("takeoff", help="列表内所有无人机起飞")
    takeoff_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    takeoff_parser.add_argument("--alt", type=float, required=True, help="起飞高度")

    # back 子命令
    back_parser = subparsers.add_parser("back", help="解除列表内所有无人机任务，立即返回")
    back_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")

    # follow 子命令
    follow_parser = subparsers.add_parser("follow", help="将目标无人机引导全部列表内无人机跟随命令")
    follow_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    follow_parser.add_argument("--follow_ip", type=str, required=True, help="目标无人机ip")
    follow_parser.add_argument("--alt", type=float, required=True, help="跟随高差")

    # stop 子命令
    stop_parser = subparsers.add_parser("stop", help="解除列表内所有无人机任务，立即悬停")
    stop_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")

    # flymission 子命令
    flymission_parser = subparsers.add_parser("flymission", help="将列表内无人机统一按顺序飞行对应的路径")
    flymission_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    flymission_parser.add_argument("--path", type=str, required=True, help="无人机飞行路径数组")
    flymission_parser.add_argument("--alt", type=float, required=True, help="不同无人机飞行高差")
    flymission_parser.add_argument("--starttime", type=float, default=-1, help="无人机从第一个点开始飞行的绝对时刻，默认立即飞行")

    # land 子命令
    land_parser = subparsers.add_parser("land", help="将列表内无人机直接着陆")
    land_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")

    # capturetime 子命令
    capturetime_parser = subparsers.add_parser("capturetime", help="将列表内无人机按照相对时间列表获取传感器数据")
    capturetime_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    capturetime_parser.add_argument("--time", type=str, required=True, help="获取传感器数据的时间列表")
    capturetime_parser.add_argument("--starttime", type=float, default=-1, help="无人机第一次获取传感器数据的绝对时刻")

    return parser


def send_command(cmd, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    parser = build_command_parser()

    args = shlex.split(cmd)
    parsed = parser.parse_args(args)

    try:
        # 获取ip
        param_dict = {k: v for k, v in vars(parsed).items() if k == "ip" and v is not None}
        ip_value = param_dict.get("ip")
        ip_list = [ip.strip("[]") for ip in ip_value.split(", ")]

        # 获取command键值对
        param_dict = {k: v for k, v in vars(parsed).items() if k != "cmd" and k != "ip" and v is not None}
        command = Command(name=parsed.cmd, params=param_dict)

        for ip in ip_list:
            # if command.name == "go":
            #     # 考虑路径文件可能比较大，单独对其传输
            #     param_dict = {k: v for k, v in vars(parsed).items() if k != "cmd" and k != "ip" and k != "path" and v is not None}
            #     new_command = Command(name=parsed.cmd, params=param_dict)
            #     path_message = new_command.to_json()
            #     sock.sendto(path_message.encode(), (ip, port))
            #     send_data.send_path(command.params["path"], ip, port)
            # else:
            command.params["ip"] = ip
            message = command.to_json()
            sock.sendto(message.encode(), (ip, port))
            print(f"已发送指令 {message} 给 {ip}\n")

    except Exception as e:
        print(f"发生错误: {e}")

    sock.close()

# 安全阈值设置（定点飞行的安全由黄子谦设置，设置最大飞行距离）
takeoff_min_alt = 5
takeoff_max_alt = 100
follow_min_alt = 3
follow_max_alt = 20
flymission_min_offset = 5
flymission_max_offset = 20
delay_time = 20
achieved_threshold = 0.2
LISTEN_IP = "0.0.0.0"  # 监听所有网卡

def distance_3d(x1, y1, z1, x2, y2, z2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

def flymission(ip, path_time_file, offset, port=9999):
    if len(ip) == 0:
        print("请指定接收命令的无人机ip！")
        return

    for i in range(len(ip)):
        dist = math.sqrt(offset[3*i]**2 + offset[3*i+1]**2 + offset[3*i+2]**2)
        if dist < follow_min_alt or dist > follow_max_alt:
            print(f"飞行偏移距离的范围为({flymission_min_offset}, {flymission_max_offset})，命令设置不符合要求！")
            return

    path_time = []
    try:
        with open(path_time_file, 'r') as f:
            for line in f:
                # 移除首尾空白，分割每行数据
                items = line.strip().split()
                if len(items) != 4:
                    print(f"错误：文件格式应为N×4矩阵，但当前行有 {len(items)} 个数据！")
                    return
                path_time.extend([float(item) for item in items])
    except FileNotFoundError:
        print(f"错误：文件 {path_time_file} 不存在！")
        return
    except ValueError:
        print("错误：文件中包含非数字内容！")
        return
    except Exception as e:
        print(f"读取文件时出错：{e}")
        return


    if len(path_time) % 4 != 0:
        print(f"飞行路径不为N*4矩阵，格式错误！")
        return

    # 解析路径和拍照时间
    capture_time = []
    path = []
    for j in range(len(path_time)):
        if j % 4 == 3:
            capture_time.append(path_time[j])
        else:
            path.append(path_time[j])

    # 发送第一个航点到所有无人机
    target_first_path = {}
    for i in range(len(ip)):
        this_first_path = [a + b for a, b in zip(path[0:3], offset[3*i:3*(i+1)])]
        target_first_path[ip[i]] = this_first_path
        send_command(f"flymission --ip ['{ip[i]}'] --path '{this_first_path}'", port)

    # 设置UDP监听
    print(f"监听UDP端口 {port} 中...（Ctrl+C 可退出）")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((LISTEN_IP, port))
        sock.setblocking(False)
    except OSError as e:
        print(f"端口 {port} 无法绑定（可能已被占用）：{e}")
        sys.exit(1)

    achieved_ips = set()  # 记录已到达的无人机IP
    start_time = time.time()
    timeout = 60  # 60秒超时

    while True:
        # 检查超时
        if time.time() - start_time > timeout:
            print("等待无人机到达超时")
            break

        # 检查UDP数据
        try:
            readable, _, _ = select.select([sock], [], [], 0.1)
            if readable:
                data, addr = sock.recvfrom(4096)
                message = data.decode().split()

                if message[0] == "state" and addr[0] in target_first_path:
                    current_pos = [float(message[1]), float(message[2]), float(message[3])]
                    target_pos = target_first_path[addr[0]]

                    if distance_3d(current_pos[0], current_pos[1], current_pos[2], target_pos[0], target_pos[1], target_pos[2]) < achieved_threshold:
                        achieved_ips.add(addr[0])
                        print(f"无人机 {addr[0]} 已到达目标位置")

                        # 检查是否所有无人机都到达
                        if len(achieved_ips) == len(ip):
                            print("所有无人机已到达目标位置")
                            break
        except Exception as e:
            print(f"解析异常: {e}")
            continue

    # 所有无人机到达后发送后续指令
    if len(achieved_ips) == len(ip):
        start_timestamp = time.time() + delay_time

        # 发送剩余航点
        for i in range(len(ip)):
            this_path = path[3:]
            for j in range(int(len(this_path)/3)):
                this_path[3 * j] += offset[3 * i]
                this_path[3 * j + 1] += offset[3 * i + 1]
                this_path[3 * j + 2] += offset[3 * i + 2]
            send_command(f"flymission --ip ['{ip[i]}'] --path '{this_path}' --starttime {start_timestamp}", port)

        # 发送拍照指令
        send_command(f"capturetime --ip '{ip}' --path '{capture_time}' --starttime {start_timestamp}", port)
    else:
        print(f"只有 {len(achieved_ips)}/{len(ip)} 架无人机到达目标位置")

    sock.close()


def takeoff(ip, alt, port=9999):
    if len(ip) != 0:
        if alt >= takeoff_min_alt and alt <= takeoff_max_alt:
            send_command(f"takeoff --ip '{ip}' --alt {alt} ", port)
        else:
            print(f"起飞抬升高度的范围为({takeoff_min_alt}, {takeoff_max_alt})，命令设置不符合要求！")
    else:
        print("请指定接收命令的无人机ip！")


def back(ip, port=9999):
    if len(ip) != 0:
        send_command(f"back --ip '{ip}' ", port)
    else:
        print("请指定接收命令的无人机ip！")

def stop(ip, port=9999):
    if len(ip) != 0:
        send_command(f"stop --ip '{ip}'", port)
    else:
        print("请指定接收命令的无人机ip！")


def follow(ip, follow_ip, alt, port=9999):
    if len(ip) != 0:
        if alt >= follow_min_alt and alt <= follow_max_alt:
            send_command(f"follow --ip '{ip}' --follow_ip '{follow_ip}' --alt {alt}", port)
        else:
            print(f"跟随高差的范围为({follow_min_alt}, {follow_max_alt})，命令设置不符合要求！")
    else:
        print("请指定接收命令的无人机ip！")

def land(ip, port=9999):
    if len(ip) != 0:
        send_command(f"land --ip '{ip}'", port)
    else:
        print("请指定接收命令的无人机ip！")


def send_message(ip_list, message, port=9999):
    message = "message " + message
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for ip in ip_list:
        sock.sendto(message.encode(), (ip, port))
        print(f"已发送指令 {message} 给 {ip}\n")

    sock.close()



# 帮助
def command_help():
    print("可用命令及说明如下：")

    print("1. takeoff(ip, alt, port=9999)")
    print("   所有指定ip的无人机起飞，飞至指定高度alt(m)")

    print("2. back(ip, port=9999)")
    print("   所有指定ip的无人机终止任务，返回起飞位置")

    print("3. follow(ip, follow_ip, alt, port=9999)")
    print("   所有指定follow_ip的无人机跟随目标无人机ip，不同无人机之间在相差alt(m)高度飞行")

    print("4. stop(ip, port=9999)")
    print("   所有指定ip的无人机立即悬停，解除任务")

    print("5. flymission(ip, path_time_file, alt, port=9999)")
    print("   所有指定ip的无人机按顺序飞行路径path_time([x1, y1, z1, t1, x2, y2, z2, t2,...])并在对应时刻拍照(存储在path_time_file中)，若有多台无人机，每台无人机与主路径的差由参数offset(m)提供")

    print("6. land(ip, port=9999)")
    print("   所有指定ip的无人机立即着陆")

    print("8. ip = search(port = 9999, timeout = 1)")
    print("   搜索所有正在监听的无人机，返回ip列表")


# if __name__ == "__main__":
#     send_message(["10.101.121.28"], "state 1 1 1 1 0 0 0.2", 10001)


