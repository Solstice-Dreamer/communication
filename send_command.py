import socket
import json
import shlex
import argparse
from dataclasses import dataclass, asdict


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

    # start 子命令
    start_parser = subparsers.add_parser("start", help="列表内所有无人机起飞")
    start_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    start_parser.add_argument("--alt", type=float, required=True, help="起飞高度")

    # back 子命令
    back_parser = subparsers.add_parser("back", help="解除列表内所有无人机任务，立即返回")
    back_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    back_parser.add_argument("--alt", type=float, required=True, help="返回时抬升的高度")
    # 无额外参数

    # follow 子命令
    follow_parser = subparsers.add_parser("follow", help="将列表内无人机全部跟随目标无人机命令")
    follow_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    follow_parser.add_argument("--follow_ip", type=str, required=True, help="目标无人机ip")
    follow_parser.add_argument("--alt", type=float, required=True, help="跟随高差")

    # release 子命令
    release_parser = subparsers.add_parser("release", help="解除列表内所有无人机任务，立即悬停")
    release_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")

    # go 子命令
    go_parser = subparsers.add_parser("go", help="将列表内无人机统一按顺序飞行对应的路径")
    go_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    go_parser.add_argument("--path", type=str, required=True, help="无人机飞行路径数组")
    go_parser.add_argument("--interval", type=float, required=True, help="执行命令时间间隔")

    # land 子命令
    land_parser = subparsers.add_parser("land", help="将列表内无人机直接着陆")
    land_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")

    # flytopoint 子命令
    flytopoint_parser = subparsers.add_parser("flytopoint", help="将列表内无人机统一按顺序飞行至对应点")
    flytopoint_parser.add_argument("--ip", type=str, required=True, help="执行命令的无人机ip")
    flytopoint_parser.add_argument("--x", type=float, required=True, help="x坐标")
    flytopoint_parser.add_argument("--y", type=float, required=True, help="y坐标")
    flytopoint_parser.add_argument("--z", type=float, required=True, help="z坐标")

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
start_min_alt = 5
start_max_alt = 100
back_min_alt = 5
back_max_alt = 100
follow_min_alt = 1
follow_max_alt = 3
go_min_interval = 5
go_max_interval = 30

def go(ip, path, interval=10, port=9999):
    if len(ip) != 0:
        if interval >= go_min_interval and interval <= go_max_interval:
            send_command(f"go --ip '{ip}' --path '{path}' --interval {interval}", port)
        else:
            print(f"时间间隔的范围为({go_min_interval}, {go_max_interval})，命令设置不符合要求！")
    else:
        print("请指定接收命令的无人机ip！")

def start(ip, alt, port=9999):
    if len(ip) != 0:
        if alt >= start_min_alt and alt <= start_max_alt:
            send_command(f"start --ip '{ip}' --alt {alt} ", port)
        else:
            print(f"起飞抬升高度的范围为({start_min_alt}, {start_max_alt})，命令设置不符合要求！")
    else:
        print("请指定接收命令的无人机ip！")



def back(ip, alt, port=9999):
    if len(ip) != 0:
        if alt >= back_min_alt and alt <= back_max_alt:
            send_command(f"back --ip '{ip}' --alt {alt} ", port)
        else:
            print(f"返回抬升高度的范围为({back_min_alt}, {back_max_alt})，命令设置不符合要求！")
    else:
        print("请指定接收命令的无人机ip！")

def release(ip, port=9999):
    if len(ip) != 0:
        send_command(f"release --ip '{ip}'", port)
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


def flytopoint(ip, x, y, z, port=9999):
    if len(ip) != 0:
        send_command(f"flytopoint --ip '{ip}' --x {x} --y {y} --z {z}", port)
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

    print("1. start(ip, alt, port=9999)")
    print("   所有指定ip的无人机起飞，飞至指定高度alt(m)")

    print("2. back(ip, alt, port=9999)")
    print("   所有指定ip的无人机终止任务，拉升至指定高度alt(m)后返回")

    print("3. follow(ip, follow_ip, alt, port=9999)")
    print("   所有指定follow_ip的无人机跟随目标无人机ip，不同无人机之间在相差alt(m)高度飞行")

    print("4. release(ip, port=9999)")
    print("   所有指定ip的无人机立即悬停，解除任务")

    print("5. go(ip, path, interval=10, port=9999)")
    print("   所有指定ip的无人机按顺序飞行路径path([x1, y1, z1, x2, y2, z2,...])，发送指令给不同无人机的时间间隔为interval(s)")

    print("6. land(ip, port=9999)")
    print("   所有指定ip的无人机立即着陆")

    print("7. flytopoint(ip, x, y, z, port=9999)")
    print("   所有指定ip的无人机飞至指定点(x, y, z)")

    print("8. ip = search(port = 9999, timeout = 1)")
    print("   搜索所有正在监听的无人机，返回ip列表")

    print("注意：局部坐标系下，z轴垂直地面向下。")

# if __name__ == "__main__":
#     send_message(["10.101.121.28"], "state 1 1 1 1 0 0 0.2", 10001)


