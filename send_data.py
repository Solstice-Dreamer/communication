import socket
import numpy as np
import pickle
import math
import time

def send_data(info, target_ips, port=10000, tag="default"):
    """
    用 UDP 将数组 info 和字符串 tag 发送到 target_ip。
    自动分片、打包、发送。
    """
    try:
        if not isinstance(info, np.ndarray) :
            raise ValueError("数据必须是 numpy 数组")
        if not isinstance(target_ips, list):
            target_ips = [target_ips]

        # 打包数据为 dict
        data_dict = {
            "tag": tag,
            "shape": info.shape,
            "dtype": str(info.dtype),
            "data": info.tobytes()
        }

        # 序列化为二进制数据
        serialized = pickle.dumps(data_dict)

        # 分片大小（建议 ≤ 1400 字节）
        CHUNK_SIZE = 1024
        total_chunks = math.ceil(len(serialized) / CHUNK_SIZE)

        # 用当前时间戳作为唯一 ID，便于接收端拼接
        uid = int(time.time() * 1000) % 1_000_000

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)

        for i in range(total_chunks):
            # 提取每一片数据
            chunk_data = serialized[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]

            # 包头结构：uid|total|index|payload
            header = {
                "uid": uid,
                "total": total_chunks,
                "index": i
            }

            # 将头和数据打包
            packet = pickle.dumps({"header": header, "payload": chunk_data})

            try:
                for ip in target_ips:
                    sock.sendto(packet, (ip, port))
            except Exception as e:
                print(f"[发送片 {i}/{total_chunks}] 异常: {e}")
                continue

        print(f"[发送成功] UID={uid} 共发送 {total_chunks} 个数据包")

    except Exception as e:
        print(f"[发送失败] 异常: {e}")

def send_path(path_file, target_ips, port=10000):
    path_xyz = np.loadtxt(path_file)
    # path_xyz = np.load(path_file)
    send_data(path_xyz, target_ips, port, "path")