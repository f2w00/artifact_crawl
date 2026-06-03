import json
import os
import random
import time
from datetime import datetime

import yt_dlp

# ===================== 路径配置 =====================

#  opera 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 你的 jsonl 文件：opera/links/bili_opera.jsonl
JSONL_FILE = os.path.join(BASE_DIR, "/downloaders/links", "bili_opera.jsonl")

# B站 cookie 文件：opera/bili_cookie.txt
COOKIE_FILE = os.path.join(BASE_DIR, "bili_cookie.txt")

# 下载保存目录：opera/output
OUTPUT_ROOT = os.path.join(BASE_DIR, "output")

# 下载记录文件：opera/downloaded.json
RECORD_FILE = os.path.join(BASE_DIR, "downloaded.json")

# 下载格式
# 优先 720p，失败后自动降级到可用格式
FORMAT = "bv*[height<=720]+ba/best[height<=720]/bv*+ba/best"

# 每个视频最多重试次数
MAX_RETRIES = 3

# 每个视频下载完成后随机等待
SLEEP_MIN = 10
SLEEP_MAX = 30

# ===================================================


os.makedirs(OUTPUT_ROOT, exist_ok=True)


def now_time():
    return datetime.now().isoformat(timespec="seconds")


def load_downloaded():
    """加载下载记录"""
    if os.path.exists(RECORD_FILE):
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("⚠️ downloaded.json 读取失败，将重新创建记录文件。")
            return {}
    return {}


downloaded = load_downloaded()


def save_downloaded():
    """保存下载记录"""
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(downloaded, f, ensure_ascii=False, indent=2)


def build_ydl_opts(output_template):
    """构建 yt-dlp 配置"""
    ydl_opts = {
        "format": FORMAT,
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        # 不下载播放列表，只下载当前视频
        "noplaylist": True,
        # 已存在文件不覆盖
        "nooverwrites": True,
        # 断点续传
        "continuedl": True,
        # yt-dlp 内部重试
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        # 网络超时
        "socket_timeout": 30,
        # 输出信息
        "quiet": False,
        "no_warnings": False,
        # 遇到错误抛出，方便记录 failed
        "ignoreerrors": False,
    }

    if os.path.exists(COOKIE_FILE):
        ydl_opts["cookiefile"] = COOKIE_FILE
    else:
        print(f"⚠️ 未找到 cookie 文件：{COOKIE_FILE}")
        print("   将不使用 cookie 下载，部分 B 站视频可能无法下载。")

    return ydl_opts


def download_video(opera_id, opera_name, bvid, url):
    """下载单个视频"""
    key = f"{opera_id}_{bvid}"

    rec = downloaded.get(key)

    if rec and rec.get("status") == "success":
        print(f"⏭️ 已跳过，之前已下载：{key}")
        print(f"   剧目：{rec.get('opera_name', opera_name)}")
        print(f"   时间：{rec.get('timestamp', '?')}")
        return "skipped"

    if rec and rec.get("status") == "failed":
        print(f"♻️ 准备重试之前失败的视频：{key}")
        print(f"   上次失败原因：{rec.get('error', '?')}")

    print(f"🔽 开始下载：{key}")
    print(f"   剧目：{opera_name}")
    print(f"   链接：{url}")

    output_template = os.path.join(OUTPUT_ROOT, f"{key}.%(ext)s")
    ydl_opts = build_ydl_opts(output_template)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"   第 {attempt}/{MAX_RETRIES} 次尝试下载...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
                info = ydl.extract_info(url, download=True)

            title = ""
            duration = None
            uploader = ""

            if isinstance(info, dict):
                title = info.get("title", "")
                duration = info.get("duration", None)
                uploader = info.get("uploader", "")

            downloaded[key] = {
                "status": "success",
                "opera_id": opera_id,
                "opera_name": opera_name,
                "bvid": bvid,
                "url": url,
                "title": title,
                "duration": duration,
                "uploader": uploader,
                "timestamp": now_time(),
            }
            save_downloaded()

            print(f"✅ 下载完成：{key}")
            if title:
                print(f"   标题：{title}")
            if duration:
                print(f"   时长：{duration} 秒")
            print()

            return "success"

        except Exception as e:
            error_msg = str(e)

            downloaded[key] = {
                "status": "failed",
                "opera_id": opera_id,
                "opera_name": opera_name,
                "bvid": bvid,
                "url": url,
                "error": error_msg,
                "timestamp": now_time(),
            }
            save_downloaded()

            print(f"❌ 下载失败：{key}")
            print(f"   错误：{error_msg}")

            if "Requested format is not available" in error_msg:
                print("   说明：该视频没有当前优先格式。")
                print("   可以单独执行下面命令查看格式：")
                print(f'   yt-dlp --cookies "{COOKIE_FILE}" -F "{url}"')

            if attempt < MAX_RETRIES:
                retry_sleep = random.uniform(15, 40)
                print(f"   等待 {retry_sleep:.1f} 秒后重试...\n")
                time.sleep(retry_sleep)
            else:
                print("🚫 已达到最大重试次数，跳过该视频。\n")
                return "failed"


def main():
    print("========================================")
    print("🎬 B站京剧视频批量下载任务开始")
    print("========================================")
    print(f"项目根目录：{BASE_DIR}")
    print(f"JSONL 文件：{JSONL_FILE}")
    print(f"Cookie 文件：{COOKIE_FILE}")
    print(f"输出目录：{OUTPUT_ROOT}")
    print(f"下载记录：{RECORD_FILE}")
    print(f"下载格式：{FORMAT}")
    print("========================================\n")

    if not os.path.exists(JSONL_FILE):
        print(f"❌ 找不到 JSONL 文件：{JSONL_FILE}")
        return

    total_count = 0
    success_count = 0
    failed_count = 0
    skipped_count = 0
    invalid_count = 0

    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
            except Exception as e:
                print(f"❌ 第 {line_no} 行 JSON 解析失败，已跳过。")
                print(f"   错误：{e}")
                invalid_count += 1
                continue

            opera_id = data.get("opera_id")
            opera_name = data.get("opera_name", "未知剧目")
            videos = data.get("videos", [])

            if not opera_id:
                print(f"⚠️ 第 {line_no} 行缺少 opera_id，已跳过。")
                invalid_count += 1
                continue

            if not videos:
                print(f"⚠️ 第 {line_no} 行没有 videos，已跳过。")
                invalid_count += 1
                continue

            print("\n========================================")
            print(f"🎭 处理戏曲：{opera_name}")
            print(f"🆔 剧目 ID：{opera_id}")
            print(f"🎬 视频数量：{len(videos)}")
            print("========================================")

            for idx, video in enumerate(videos, 1):
                bvid = video.get("bvid")
                url = video.get("url")

                if not bvid or not url:
                    print(f"⚠️ 第 {line_no} 行第 {idx} 个视频缺少 bvid 或 url，已跳过。")
                    invalid_count += 1
                    continue

                total_count += 1

                print(f"\n[{idx}/{len(videos)}] 当前视频：{opera_id}_{bvid}")

                result = download_video(
                    opera_id=opera_id, opera_name=opera_name, bvid=bvid, url=url
                )

                if result == "success":
                    success_count += 1
                elif result == "failed":
                    failed_count += 1
                elif result == "skipped":
                    skipped_count += 1

                if result == "success":
                    sleep_time = random.uniform(SLEEP_MIN, SLEEP_MAX)
                    print(f"⏳ 等待 {sleep_time:.1f} 秒后继续...\n")
                    time.sleep(sleep_time)

    print("\n🎉 全部任务处理完成！")
    print("========================================")
    print(f"总视频数：{total_count}")
    print(f"成功下载：{success_count}")
    print(f"下载失败：{failed_count}")
    print(f"已跳过：{skipped_count}")
    print(f"无效数据：{invalid_count}")
    print(f"下载目录：{OUTPUT_ROOT}")
    print(f"记录文件：{RECORD_FILE}")
    print("========================================")


if __name__ == "__main__":
    main()
