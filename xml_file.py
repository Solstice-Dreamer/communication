import os
import xml.etree.ElementTree as ET
from datetime import datetime

def save_command_to_xml(out_dir, command_dict):
    # 创建保存目录
    os.makedirs(out_dir, exist_ok=True)

    cmd_name = command_dict.get("name", "unknown")
    params = command_dict.get("params", {})

    root = ET.Element("Command")
    name_elem = ET.SubElement(root, "Name")
    name_elem.text = cmd_name

    params_elem = ET.SubElement(root, "Parameters")
    for key, value in params.items():
        param_elem = ET.SubElement(params_elem, key)
        param_elem.text = str(value)

    # 自动生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{cmd_name}_{timestamp}.xml.part"
    filepath = os.path.join(out_dir, filename)

    try:
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        print(f"写入XML文件失败: {e}")
        return

    new_filename = f"{cmd_name}_{timestamp}.xml"
    new_filepath = os.path.join(out_dir, new_filename)
    try:
        os.replace(filepath, new_filepath)  # 原子替换，更安全
    except Exception as e:
        print(f"重命名文件失败: {e}")
        return

    print(f"已保存XML指令: {new_filepath}")