import socket
import time

def search(port = 9999, timeout = 1):
    message = "message ping"  # 探针消息

    #测试一下255是不是广播ip
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    # 发送广播探针包
    sock.sendto(message.encode(), ('<broadcast>', port))
    print(f"已广播 UDP 探针: {message} (端口 {port})")

    # 接收回应
    found_ip = set()
    start_time = time.time()
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            data_de = data.decode()
            if data_de[8:] == "message reached":
                print(f"收到回应: {data_de[8:]} 来自 {addr[0]}")
                found_ip.add(addr[0])
        except socket.timeout:
            break
        if time.time() - start_time > timeout:
            break

    sock.close()
    print("\n 发现的设备 ip, port:")
    for ip in found_ip:
        print(f"  -{ip}:{port}")
    return list(found_ip)



# import socket
# import time
# from send_command import send_message
#
# def search(port = 9999, timeout = 1):
#     message = "message ping"  # 探针消息
#
#     #测试一下255是不是广播ip
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#     sock.settimeout(timeout)
#
#     # 发送广播探针包
#     sock.sendto(message.encode(), ('<broadcast>', port))
#     print(f"已广播 UDP 探针: {message} (端口 {port})")
#
#     # 接收回应
#     found_ip = set()
#     start_time = time.time()
#     while True:
#         try:
#             data, addr = sock.recvfrom(1024)
#             if data.decode() == "message reached!":
#                 print(f"收到回应: {data.decode()} 来自 {addr[0]}")
#                 found_ip.add(addr[0])
#         except socket.timeout:
#             break
#         if time.time() - start_time > timeout:
#             break
#
#     sock.close()
#     print("\n 发现的设备 ip, port:")
#     for ip in found_ip:
#         print(f"  -{ip}:{port}")
#     return list(found_ip)
#
# # if __name__ == "__main__":
# #     # 创建 UDP socket（广播 + 接收回应）
# #     PORT = int(input("请输入接收端端口: ").strip())
# #     devices = search(PORT, 10)
# #     print(devices)
