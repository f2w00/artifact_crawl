#!/bin/bash

DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$DIR/../.." && pwd)"

exclude_files=("method.py" "run.sh")

scripts=()
while IFS= read -r f; do
    name=$(basename "$f")
    skip=false
    for ex in "${exclude_files[@]}"; do
        if [ "$name" = "$ex" ]; then
            skip=true
            break
        fi
    done
    $skip || scripts+=("$name")
done < <(find "$DIR" -maxdepth 1 -name '*.py' -type f | sort)

if [ ${#scripts[@]} -eq 0 ]; then
    echo "没有可执行的脚本"
    exit 1
fi

echo "请选择要执行的脚本:"
for i in "${!scripts[@]}"; do
    echo "  $((i+1))) ${scripts[$i]}"
done

read -r -p "输入编号 (1-${#scripts[@]}): " choice

if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#scripts[@]}" ]; then
    echo "无效选择"
    exit 1
fi

selected="${scripts[$((choice-1))]}"
script_path="$DIR/$selected"
log_file="$DIR/output_${selected%.py}.log"

shift $((OPTIND))
remaining="$*"

cd "$PROJECT_DIR" || exit 1

nohup uv run "$script_path" $remaining > "$log_file" 2>&1 &

echo "已启动: $selected"
echo "日志文件: ${log_file}"
echo "进程ID: $!"
echo "查看日志: tail -f ${log_file}"
echo "查看进程: ps aux | grep ${selected%.py}.py"
