import os
import time
import xml.etree.ElementTree as ET
import multi_point_fly

# 设置扫描的文件夹路径
folder_path = './commands_xml'

# 设置扫描的时间间隔（秒）
scan_interval = 5

def read_xml_file(file_path):
    """读取并解析 XML 文件并输出命令格式"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # 获取命令名称
        command_name = root.find('Name').text
        
        # 获取参数并生成命令字符串
        parameters = root.find('Parameters')
        command_str = f"{command_name}"

        para_dict = {}
        # 遍历参数
        for param in parameters:
            param_name = param.tag
            param_value = param.text
            para_dict[param_name] = param_value
            command_str += f" --{param_name} {param_value}"
        
        # 输出结果
        print(command_str)
        return command_name, para_dict
    except Exception as e:
        print(f"读取 {file_path} 时发生错误：{e}")

def scan_folder():
    """定时扫描文件夹并读取 XML 文件"""
    while True:
        print("开始扫描文件夹...")
        
        # 获取文件夹中的所有文件
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            # 检查是否为 XML 文件
            if filename.endswith('.xml') and os.path.isfile(file_path):
                print(f"发现 XML 文件: {filename}")
                command, para = read_xml_file(file_path)
                new_filepath = file_path + ".finish"
                os.rename(file_path, new_filepath)

                if command == "back":
                    multi_point_fly.execute_back(float(para["alt"]))
                if command == "follow":
                    ip_list = [ip.strip("[]") for ip in para["follow_ip"].split(", ")]
                    multi_point_fly.execute_follow(ip_list, float(para["alt"]))
        
        # 等待下次扫描
        time.sleep(scan_interval)

if __name__ == '__main__':
    scan_folder()
