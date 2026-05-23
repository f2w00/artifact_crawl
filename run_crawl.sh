#!/bin/bash

# 爬虫运行脚本
# 用法: ./run_crawler.sh <脚本名称(不含.py后缀)>
# 示例: ./run_crawler.sh hn
# 示例: ./run_crawler.sh ln

if [ -z "$1" ]; then
    echo "用法: $0 <脚本名称(不含.py后缀)>"
    echo "示例: $0 hn"
    echo "示例: $0 ln"
    exit 1
fi

CRAWLER_NAME=$1
CRAWL_DIR="./crawlers"

# 检查爬虫脚本是否存在
if [ ! -f "${CRAWL_DIR}/${CRAWLER_NAME}.py" ]; then
    echo "错误: ${CRAWL_DIR}/${CRAWLER_NAME}.py 不存在"
    exit 1
fi

# 进入爬虫目录
cd "$CRAWL_DIR" || exit 1

# 使用nohup后台运行
nohup python "${CRAWLER_NAME}.py" > "output_${CRAWLER_NAME}.log" 2>&1 &

echo "爬虫 ${CRAWLER_NAME}.py 已在后台启动"
echo "日志文件: ${CRAWL_DIR}/output_${CRAWLER_NAME}.log"
echo "进程ID: $!"
echo "查看日志: tail -f ${CRAWL_DIR}/output_${CRAWLER_NAME}.log"
echo "查看进程: ps aux | grep ${CRAWLER_NAME}.py"
