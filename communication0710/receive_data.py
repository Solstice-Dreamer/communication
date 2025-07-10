import socket
import pickle
import numpy as np
import os
import time

def save_path_to_txt(out_dir, filename, data):
    # 创建保存目录
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, filename)
    np.savetxt(filepath, data)

def receive_data(sock):
    # 缓存结构 { uid: { index: payload_bytes } }
    buffer_dict = {}
    timestamp_dict = {}
    timeout = 10

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            packet = pickle.loads(data)

            header = packet["header"]
            payload = packet["payload"]

            uid = header["uid"]
            total = header["total"]
            index = header["index"]

            # 初始化缓存结构
            if uid not in buffer_dict:
                buffer_dict[uid] = {}
                timestamp_dict[uid] = time.time()

            buffer_dict[uid][index] = payload
            timestamp_dict[uid] = time.time()

            print(f"[接收] UID={uid} index={index+1}/{total} 来自 {addr[0]}")

            # 判断是否接收完
            if len(buffer_dict[uid]) == total:
                print(f"[完成] 收到 UID={uid} 的全部 {total} 个包，开始重组")

                # 重组完整的 serialized 数据
                serialized = b''.join(buffer_dict[uid][i] for i in range(total))
                data_dict = pickle.loads(serialized)

                tag = data_dict.get("tag", "unknown")
                shape = data_dict["shape"]
                dtype = data_dict["dtype"]
                raw_bytes = data_dict["data"]

                # 还原为 numpy 数组
                arr = np.frombuffer(raw_bytes, dtype=dtype).reshape(shape)

                print(f"[成功] 接收到数据 tag={tag} shape={shape} dtype={dtype}")

                if tag == "path":
                    save_path_to_txt("./path", f"received_path_{uid}.txt", arr)
                    print(f"[保存] 路径数据已保存为 /path/received_path_{uid}.txt")
                else:
                    print(f"[提示] 收到未处理类型数据 tag={tag}")

                # 清理
                del buffer_dict[uid]
                del timestamp_dict[uid]
                break


            # 清理超时数据
            now = time.time()
            for old_uid in list(timestamp_dict):
                if now - timestamp_dict[old_uid] > timeout:
                    print(f"[超时] 清理 UID={old_uid}")
                    buffer_dict.pop(old_uid, None)
                    timestamp_dict.pop(old_uid, None)

        except Exception as e:
            print(f"[错误] {e}")
