#!/bin/bash

if [ $# -lt 1 ]; then
    echo "用法: $0 <脚本路径> [参数...]"
    echo "示例: $0 file2db/xform/append.py 2"
    echo "示例: $0 file2db/xform/import_result.py"
    exit 1
fi

SCRIPT=$1
shift

if [ ! -f "$SCRIPT" ]; then
    echo "错误: $SCRIPT 不存在"
    exit 1
fi

SCRIPT_NAME=$(basename "$SCRIPT" .py)
LOG_DIR="$(dirname "$SCRIPT")"
LOG_FILE="${LOG_DIR}/output_${SCRIPT_NAME}.log"

nohup uv run "$SCRIPT" "$@" > "$LOG_FILE" 2>&1 &

echo "脚本 ${SCRIPT} 已在后台启动"
echo "日志文件: ${LOG_FILE}"
echo "进程ID: $!"
echo "查看日志: tail -f ${LOG_FILE}"
echo "查看进程: ps aux | grep ${SCRIPT_NAME}.py"
