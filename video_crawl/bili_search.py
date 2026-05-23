import importlib
import json
import os
import random
import re
import sys
import time

import requests

# B站搜索API (v2接口不受IP封禁影响)
SEARCH_API = "https://api.bilibili.com/x/web-interface/search/all/v2"

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


def clean_title(title):
    """清理标题中的HTML标签"""
    if not title:
        return ""
    title = re.sub(r"<em[^>]*>", "", title)
    title = re.sub(r"</em>", "", title)
    return title.strip()


def format_duration(seconds):
    """将秒数转换为 MM:SS 格式"""
    if not seconds:
        return "00:00"
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "00:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def format_timestamp(timestamp):
    """将时间戳转换为可读格式"""
    if not timestamp:
        return ""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def search_bilibili(keyword, max_results=10):
    """搜索B站视频"""
    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": 1,
        "page_size": max_results,
        "order": "totalrank",
    }
    try:
        response = requests.get(SEARCH_API, params=params, headers=headers, timeout=30)
        response.encoding = "utf-8"
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                print(f"  响应类型异常: Content-Type={content_type}")
                return None
            data = response.json()
            if data.get("code") == -352:
                print(f"  B站风控拦截: {data.get('message', '')}")
                return None
            return data
        else:
            print(f"  HTTP错误: {response.status_code}")
            return None
    except requests.exceptions.JSONDecodeError:
        print(f"  JSON解析失败，B站可能返回了HTML（被风控）")
        return None
    except Exception as e:
        print(f"  请求失败: {e}")
        return None


def extract_video_info(item):
    """提取视频信息"""
    bvid = item.get("bvid", "")
    duration_raw = item.get("duration", 0)
    if isinstance(duration_raw, str) and ":" in duration_raw:
        duration_str = duration_raw
    else:
        duration_str = format_duration(duration_raw)
    return {
        "title": clean_title(item.get("title", "")),
        "url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
        "duration": duration_raw,
        "duration_str": duration_str,
        "author": item.get("author", ""),
        "pubdate": item.get("pubdate", 0),
        "pubdate_str": format_timestamp(item.get("pubdate", 0)),
        "play": item.get("play", 0),
        "bvid": bvid,
    }


def load_completed_names(output_file):
    """加载已完成的剧目名称（用于断点续爬）"""
    completed = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            completed.add(item.get("opera_name"))
                        except:
                            continue
        except:
            pass
    return completed


def append_to_jsonl(output_file, result):
    """追加一条结果到JSONL文件"""
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python -m video_crawl.bili_search <模块名>")
        sys.exit(1)

    module_name = sys.argv[1]

    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 动态导入模块
    try:
        mod = importlib.import_module(f"video_crawl.{module_name}")
    except ModuleNotFoundError:
        print(f"错误: 找不到模块 video_crawl.{module_name}")
        sys.exit(1)

    # 调用 get_opera_meta()
    if not hasattr(mod, "get_opera_meta"):
        print(f"错误: 模块 {module_name} 不存在 get_opera_meta() 函数")
        sys.exit(1)

    try:
        keyword_prefix, module_id, opera_list = mod.get_opera_meta()
    except Exception as e:
        print(f"错误: 调用 get_opera_meta() 失败: {e}")
        sys.exit(1)

    OUTPUT_FILE = os.path.join(BASE_DIR, "output", "video_search", f"{module_id}.jsonl")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    total_count = len(opera_list)
    print(f"开始搜索 {total_count} 部{keyword_prefix}剧目...")
    print(f"输出文件: {OUTPUT_FILE}\n")

    # 加载已完成的剧目名称（断点续爬）
    completed_names = load_completed_names(OUTPUT_FILE)
    print(f"已搜索: {len(completed_names)} 个剧目\n")

    success_count = 0
    fail_count = 0

    for idx, (num, name, type_, role) in enumerate(opera_list, 1):
        # 跳过已完成的
        if name in completed_names:
            print(f"[{idx}/{total_count}] 跳过已搜索: {name}")
            continue

        keyword = f"{keyword_prefix} {name} 全集"
        print(f"[{idx}/{total_count}] 搜索: {keyword}")

        try:
            data = search_bilibili(keyword, max_results=10)

            if data is None:
                print(f"  搜索失败，停止运行")
                sys.exit(1)

            if data.get("code") != 0:
                print(f"  API返回非零code({data.get('code')})，停止运行")
                sys.exit(1)

            result_list = data.get("data", {}).get("result", [])
            videos = []
            for item in result_list:
                if item.get("result_type") == "video":
                    for v in item.get("data", []):
                        video_info = extract_video_info(v)
                        videos.append(video_info)
                    break

            print(f"  找到 {len(videos)} 个视频")

            if len(videos) == 0:
                print(f"  无视频结果，继续")
            else:
                result = {
                    "opera_id": num,
                    "opera_name": name,
                    "opera_type": type_,
                    "keyword": keyword,
                    "videos": videos,
                    "video_count": len(videos),
                }
                append_to_jsonl(OUTPUT_FILE, result)
                completed_names.add(name)
                print(f"  已追加写入JSONL文件")
                success_count += 1

            # 随机延迟，避免被限流
            if idx < total_count:
                sleep_time = random.uniform(60, 180)
                time.sleep(sleep_time)

        except SystemExit:
            raise
        except Exception as e:
            print(f"  异常: {e}，停止运行")
            sys.exit(1)

    print(f"\n完成！")
    print(f"  总剧目数: {total_count}")
    print(f"  成功搜索: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  输出文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
