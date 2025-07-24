#!/bin/bash

# 添加你想用的路径
export PYTHONPATH=/home/seob02/communication:$PYTHONPATH

# 启动 Python 并导入你需要的模块
python3 -i -c "
from search import search
from send_command import flymission
from send_command import takeoff
from send_command import back
from send_command import stop
from send_command import follow
from send_command import land
from send_command import send_message
from send_command import command_help

import os
paths = os.environ.get('PYTHONPATH', '').split(':')
path = paths[0]
print('当前工作目录: '+path)
"
