import csv
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(BASE_DIR, "store")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}
TIMEOUT = 30
MAX_FAIL_STREAK = 3


def pad_code(code):
    return str(code).zfill(6)


def parse_args(args):
    if not args:
        return None
    if args[0] == "all":
        codes = [
            f.replace(".csv", "")
            for f in os.listdir(STORE_DIR)
            if f.endswith(".csv") and "000006" not in f
        ]
    else:
        codes = [pad_code(a) for a in args]
    return codes


def load_progress(progress_path):
    completed = set()
    failed = set()
    if os.path.exists(progress_path):
        with open(progress_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    gid, status = parts[0], parts[1]
                    if status == "OK":
                        completed.add(gid)
                    elif status == "FAIL":
                        failed.add(gid)
    return completed, failed


def append_progress(progress_path, global_id, status):
    with open(progress_path, "a", encoding="utf-8") as f:
        f.write(f"{global_id} {status}\n")


def download_one(code, global_id, image_url):
    category_dir = global_id[6:11]
    dir_path = os.path.join(STORE_DIR, "images", code, category_dir)
    os.makedirs(dir_path, exist_ok=True)

    ext = ".jpg"
    url_lower = image_url.lower()
    if ".png" in url_lower:
        ext = ".png"
    elif ".jpeg" in url_lower:
        ext = ".jpeg"
    elif ".webp" in url_lower:
        ext = ".webp"

    filepath = os.path.join(dir_path, f"{global_id}{ext}")

    if os.path.exists(filepath):
        return True

    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > 0:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return True
        else:
            return False
    except Exception:
        return False


def download_museum(code):
    csv_path = os.path.join(STORE_DIR, f"{code}.csv")
    progress_path = os.path.join(STORE_DIR, code, "progress.txt")

    if not os.path.exists(csv_path):
        print(f"[{code}] CSV 文件不存在，跳过")
        return {"code": code, "total": 0, "ok": 0, "fail": 0, "last": ""}

    os.makedirs(os.path.join(STORE_DIR, code), exist_ok=True)

    rows = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if "image_url" not in headers:
            print(f"[{code}] 无 image_url 列，跳过")
            return {"code": code, "total": 0, "ok": 0, "fail": 0, "last": ""}
        for row in reader:
            rows.append(row)

    total = len(rows)
    completed, failed = load_progress(progress_path)
    done_before = len(completed) + len(failed)

    pending = [
        r
        for r in rows
        if r["global_id"] not in completed and r["global_id"] not in failed
    ]

    ok_count = 0
    fail_count = 0
    fail_streak = 0
    last_gid = max(completed) if completed else ""

    if pending:
        print(f"[{code}] 总数={total} 已处理={done_before} 本次待处理={len(pending)}")
    else:
        print(f"[{code}] 全部完成 ({total} 行)")

    for idx, row in enumerate(pending, 1):
        global_id = row["global_id"]
        image_url = row.get("image_url", "").strip()

        if not image_url:
            append_progress(progress_path, global_id, "FAIL")
            fail_count += 1
            fail_streak += 1
            if fail_streak >= MAX_FAIL_STREAK:
                print(f"  [{code}] 连续 {MAX_FAIL_STREAK} 次无图片URL，停止")
                break
            continue

        success = download_one(code, global_id, image_url)

        if success:
            append_progress(progress_path, global_id, "OK")
            ok_count += 1
            fail_streak = 0
            last_gid = str(global_id) if global_id else last_gid
        else:
            append_progress(progress_path, global_id, "FAIL")
            fail_count += 1
            fail_streak += 1
            if fail_streak >= MAX_FAIL_STREAK:
                print(f"  [{code}] 连续 {MAX_FAIL_STREAK} 次下载失败，停止")
                break

        if idx % 50 == 0:
            print(
                f"  [{code}] 进度: {idx}/{len(pending)}, OK={ok_count}, FAIL={fail_count}"
            )

        time.sleep(random.uniform(0.5, 3))

    print(f"[{code}] 完成. 本次 OK={ok_count} FAIL={fail_count}")

    return {
        "code": code,
        "total": total,
        "ok": len(completed) + ok_count,
        "fail": len(failed) + fail_count,
        "last": last_gid,
    }


def write_summary(results):
    summary_path = os.path.join(STORE_DIR, "summary.json")
    summary = {}
    if os.path.exists(summary_path):
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
    for r in results:
        summary[r["code"]] = {
            "total": r["total"],
            "ok": r["ok"],
            "fail": r["fail"],
            "last": r["last"],
        }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print("用法: python downloaders/download_images.py <博物馆编号>...")
        print("示例: python downloaders/download_images.py 0 1 3")
        print("       python downloaders/download_images.py all")
        sys.exit(1)

    codes = parse_args(sys.argv[1:])
    if not codes:
        print("未找到可处理的博物馆")
        sys.exit(1)

    print(f"博物馆: {codes}\n")

    results = []
    with ThreadPoolExecutor(max_workers=len(codes)) as pool:
        futures = {pool.submit(download_museum, code): code for code in codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                print(f"[{code}] 线程异常: {e}")

    write_summary(results)

    print(f"\n总计: {len(codes)} 个博物馆")
    total_all = sum(r["total"] for r in results)
    ok_all = sum(r["ok"] for r in results)
    fail_all = sum(r["fail"] for r in results)
    print(f"  总行数: {total_all}")
    print(f"  成功: {ok_all}")
    print(f"  失败: {fail_all}")


if __name__ == "__main__":
    main()
