#!/bin/bash

if [ -z "$1" ]; then
    echo "用法: $0 <模块名>"
    echo "示例: $0 peking"
    exit 1
fi

MODULE="$1"

PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
LOG_DIR="${PROJECT_ROOT}/output/video_search"
LOG_FILE="${LOG_DIR}/${MODULE}.log"

mkdir -p "$LOG_DIR"

cd "$PROJECT_ROOT"

echo "启动搜索任务: ${MODULE}"
echo "日志文件: ${LOG_FILE}"

source .venv/bin/activate
nohup python -m video_crawl.universal_video_search "$MODULE" > "$LOG_FILE" 2>&1 &

PID=$!
echo "PID: ${PID}"
echo "查看日志: tail -f ${LOG_FILE}"
echo "停止任务: kill ${PID}"
