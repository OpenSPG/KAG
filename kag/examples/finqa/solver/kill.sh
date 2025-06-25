#!/bin/bash

# 定义要查找的进程关键字
PROCESS_KEYWORD="python -u /home/zhenzhi/code/KAG/kag/examples/finqa/solver/eval.py"

# 查找匹配的进程ID
PIDS=$(ps aux | grep "$PROCESS_KEYWORD" | grep -v grep | awk '{print $2}')

# 检查是否找到匹配的进程
if [ -z "$PIDS" ]; then
    echo "未找到运行中的进程: $PROCESS_KEYWORD"
else
    echo "找到以下进程ID: $PIDS"
    # 遍历并杀掉每个匹配的进程
    for PID in $PIDS; do
        echo "正在终止进程ID: $PID"
        kill -9 $PID
        if [ $? -eq 0 ]; then
            echo "进程ID $PID 已成功终止"
        else
            echo "终止进程ID $PID 失败"
        fi
    done
fi
