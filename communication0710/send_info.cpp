#include <iostream>
#include <vector>
#include <string>
#include <cstring>      // for memset
#include <arpa/inet.h>  // for inet_addr, sockaddr_in (on Linux)
#include <sys/socket.h> // for socket functions
#include <unistd.h>     // for close()

struct UAV_info {
    float pos[3] = {0, 0, 0};
    float q[4] = {1, 0, 0, 0};
    float battery = 0;
};

// 发送信息（组装字符串并广播）
void send_info(const UAV_info& info, int port) {
    std::string head = "state";
    std::string message = head + " " +
                          std::to_string(info.pos[0]) + " " + std::to_string(info.pos[1]) + " " + std::to_string(info.pos[2]) + " " +
                          std::to_string(info.q[0]) + " " + std::to_string(info.q[1]) + " " + std::to_string(info.q[2]) + " " +
                          std::to_string(info.q[3]) + " " +
                          std::to_string(info.battery);

    // 发送广播
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        std::cerr << "创建UDP socket失败！\n";
        return;
    }

    // 设置 socket 为可广播
    int broadcastEnable = 1;
    if (setsockopt(sock, SOL_SOCKET, SO_BROADCAST, (char *)&broadcastEnable, sizeof(broadcastEnable)) < 0) {
        std::cerr << "设置广播选项失败！\n";
        close(sock);
        return;
    }

    sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, "10.101.121.81", &(addr.sin_addr));
    // addr.sin_addr.s_addr = inet_addr("10.101.121.255"); // 通信地址地址

    ssize_t sent = sendto(sock, message.c_str(), message.size(), 0,
                          reinterpret_cast<sockaddr*>(&addr), sizeof(addr));
    if (sent < 0) {
        std::cerr << "广播发送失败！\n";
    } else {
        std::cout << "已广播指令 \"" << message << "\" 到端口 " << port << "\n";
    }

    close(sock);
}

int main() {


    for (int i = 0; i < 10; i++){
        UAV_info uav{{116.4 + 0.001*i, 39.9+0.001*i, i}, {0, 1, 0, 0}, 100 - i};
        int port = 10001;
        send_info(uav, port);
        sleep(1);
    }

    // for (int i = 0; i < 10; i++){
    //     UAV_info uav{{0, 0, i}, {0, 1, 0, 0}, 100 - i};
    //     int port = 10001;
    //     send_info(uav, port);
    //     sleep(1);
    // }
    // sleep(15);
    // for (int i = 0; i < 5; i++){
    //     UAV_info uav{{0, i, 10}, {0, 1, 0, 0}, 90 - i};
    //     int port = 10001;
    //     send_info(uav, port);
    //     sleep(1);
    // }
    // sleep(5);
    // for (int i = 0; i < 5; i++){
    //     UAV_info uav{{i, 5, 10}, {0, 1, 0, 0}, 85 - i};
    //     int port = 10001;
    //     send_info(uav, port);
    //     sleep(1);
    // }
    // sleep(5);
    // for (int i = 0; i < 5; i++){
    //     UAV_info uav{{5, 5-i, 10}, {0, 1, 0, 0}, 80 - i};
    //     int port = 10001;
    //     send_info(uav, port);
    //     sleep(1);
    // }
    // sleep(5);
    // for (int i = 0; i < 5; i++){
    //     UAV_info uav{{5-i, 0, 10}, {0, 1, 0, 0}, 75 - i};
    //     int port = 10001;
    //     send_info(uav, port);
    //     sleep(1);
    // }
    // sleep(5);
    // for (int i = 0; i < 10; i++){
    //     UAV_info uav{{0, 0, 10-i}, {0, 1, 0, 0}, 70 - i};
    //     int port = 10001;
    //     send_info(uav, port);
    //     sleep(1);
    // }
    // sleep(5);
    // return 0;
}


// #include <iostream>
// #include <string>
// #include <cstring>
// #include <arpa/inet.h>
// #include <sys/socket.h>
// #include <unistd.h>
// #include <netinet/in.h>  // 为了跨平台统一包含

// struct UAV_info {
//     float pos[3] = {0, 0, 0};
//     float q[4] = {1, 0, 0, 0};
//     float battery = 0;
// };

// // 发送信息（组装字符串并广播）
// void send_info(const UAV_info& info, int port) {
//     // 构造消息字符串
//     std::string message = "state " +
//         std::to_string(info.pos[0]) + " " + std::to_string(info.pos[1]) + " " + std::to_string(info.pos[2]) + " " +
//         std::to_string(info.q[0]) + " " + std::to_string(info.q[1]) + " " + std::to_string(info.q[2]) + " " +
//         std::to_string(info.q[3]) + " " + std::to_string(info.battery);

//     // 创建UDP socket
//     int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
//     if (sock < 0) {
//         perror("创建 socket 失败");
//         return;
//     }

//     // 设置 socket 允许广播
//     int broadcastEnable = 1;
//     if (setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcastEnable, sizeof(broadcastEnable)) < 0) {
//         perror("设置 SO_BROADCAST 失败");
//         close(sock);
//         return;
//     }

//     // 填充目标地址结构体
//     struct sockaddr_in broadcastAddr;
//     memset(&broadcastAddr, 0, sizeof(broadcastAddr));
//     broadcastAddr.sin_family = AF_INET;
//     broadcastAddr.sin_port = htons(port);
//     broadcastAddr.sin_addr.s_addr = inet_addr("10.101.121.255");  // 替换为你网段的广播地址

//     // 发送广播消息
//     ssize_t sentBytes = sendto(sock, message.c_str(), message.size(), 0,
//                                reinterpret_cast<struct sockaddr*>(&broadcastAddr), sizeof(broadcastAddr));

//     if (sentBytes < 0) {
//         perror("广播发送失败");
//     } else {
//         std::cout << "成功广播：" << message << " 到端口 " << port << std::endl;
//     }

//     close(sock);
// }

// int main() {
//     UAV_info uav{{0, 0, 1}, {1, 0, 0, 0}, 0.5f};
//     int port = 10016;
//     send_info(uav, port);
//     return 0;
// }
