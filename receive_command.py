import socket
import json
import argparse
import sys
from xml_file import save_command_to_xml
import time

# 接收配置
LISTEN_IP = "0.0.0.0"  # 监听所有网卡

def listening(port=9999):
    print(f"监听UDP端口 {port} 中...（Ctrl+C 可退出）")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((LISTEN_IP, port))
    except OSError as e:
        print(f"端口 {port} 无法绑定（可能已被占用）：{e}")
        sys.exit(1)

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            data_de = data.decode()
            # 用于接收消息
            if data_de[:8] == "message ":
                # 确认是否能够通信
                if data_de[8:] == "ping":
                    print(f"收到消息{data_de[8:]}，来自：{addr}")
                    sock.sendto("message message reached".encode(), addr)
                # 接收发送给其他无人机消息或指令的回应
                if data_de[8:] == "message reached！" or data_de[8:] == "command reached！":
                    print(f"{data_de[8:]}，来自：{addr}")
            # 用于接收指令
            else:
                try:
                    out_dir = "./commands_xml"
                    print(f"\n收到来自 {addr} 的指令：")
                    command = json.loads(data.decode())
                    print("指令内容：", command)
                    save_command_to_xml(out_dir, command)
                    sock.sendto("message command reached".encode(), addr)

                except json.JSONDecodeError:
                    print("解析失败：不是有效的JSON")

        except KeyboardInterrupt:
            print("\n接收器已退出")
            break
        except Exception as e:
            print(f"异常: {e}")
    sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="程序运行指令")
    parser.add_argument("--port", type=int, default=9999, help="监听的UDP端口（默认10001）")
    args = parser.parse_args()

    time.sleep(5)
    listening(args.port)