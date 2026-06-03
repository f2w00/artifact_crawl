import argparse
import csv
import glob
import json
import os
import sys

import requests

DIR = os.path.dirname(__file__)
STORE_DIR = os.path.normpath(os.path.join(DIR, "..", "store"))
MAPPINGS_DIR = os.path.join(DIR, "mappings")
PROFILE_ID = "alidsv4"

TARGET_FIELDS = [
    {
        "relic_id": "文物ID,自增14位数字",
        "relic_name": "文物标准名称",
        "relic_big_type": "文物大类类别（陶器、瓷器等）",
        "relic_shape_type": "器物形制类别（如碗、盘等）",
        "relic_usage": "器物功能（如食器、酒器等）",
        "main_material": "主要基础材质（如陶、瓷等）",
        "museum_name": "馆藏单位（例如：中国国家博物馆）",
        "img_url": "文物图片链接（主图URL，多张可逗号分隔）",
        "relic_source": "文物来源方式（考古发掘 / 民间征集）",
        "relic_status": "文物保存状态（完整 / 残缺）",
        "relic_brief": "文物详细介绍）",
        "dynasty": "所属朝代",
        "history_stage": "具体时期（示例：初唐、盛唐）",
        "unearthed_address": "出土地点（省 - 市 - 县 - 遗址）",
        "site_type": "出土地类型（比如帝王墓葬、平民墓葬）",
        "culture_belong": "地域文化归属（比如中原文化、江南吴越文化）",
        "main_pattern": "纹饰特征（比如鱼纹、龙纹)",
        "pattern_make_craft": "纹饰制作工艺（如刻花、划花）",
        "pattern_position": "纹饰分布位置（如器身、器底）",
        "pattern_meaning": "纹饰文化寓意（比如羊形象征吉祥与祭祀）",
        "total_craft": "制作工艺（比如拉坯烧制、失蜡法铸造）",
        "craft_school": "工艺流派（如唐代越窑、宋代汝窑等）",
        "related_person_name": "关联人物姓名（如李世民、宋徽宗家）",
        "person_relation_type": "人物与文物关系（如烧制制作、宫廷御用）",
        "person_relation_desc": "关联人物描述",
    }
]


def rpc(method, params):
    print(params)
    return requests.post(
        # "http://10.15.22.91:8848/rpc",
        "http://localhost:8848/rpc",
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": "req"},
    ).json()


def pad_code(raw: str) -> str:
    return raw.zfill(6)


def csv_files_to_process(start_code: str | None) -> list[str]:
    pattern = os.path.join(STORE_DIR, "*.csv")
    all_csvs = sorted(glob.glob(pattern))
    if start_code is None:
        return all_csvs
    target = os.path.join(STORE_DIR, f"{start_code}.csv")
    if not os.path.exists(target):
        print(f"Error: {start_code}.csv not found in {STORE_DIR}")
        sys.exit(1)
    return [target]


def process_one(csv_path: str) -> dict | None:
    fname = os.path.basename(csv_path)
    code = fname.replace(".csv", "")

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        try:
            example = next(reader)
        except StopIteration:
            print(f"  [SKIP] {fname} is empty")
            return None

    print(f"\n[{code}] example keys: {list(example.keys())}")
    print(f"[{code}] calling mapping.field ...", end=" ", flush=True)

    resp = rpc(
        "mapping.field",
        {
            "profile_id": PROFILE_ID,
            "example": example,
            "target_fields": TARGET_FIELDS,
            "refresh": True,
        },
    )

    if "result" not in resp or "mapping" not in resp["result"]:
        print("FAILED")
        print(f"  Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")
        return None

    mapping = resp["result"]["mapping"]
    print("OK")
    print(f"[{code}] mapping:")
    for src, tgt in mapping.items():
        print(f"    {src}  →  {tgt}")

    os.makedirs(MAPPINGS_DIR, exist_ok=True)
    out_path = os.path.join(MAPPINGS_DIR, f"{code}_mapping.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)
    print(f"[{code}] saved to {out_path}")

    return mapping


def main():
    parser = argparse.ArgumentParser(
        description="Generate field mappings from store CSVs"
    )
    parser.add_argument("--code", help="Museum code (e.g. 3 → process only 000003.csv)")
    args = parser.parse_args()

    start = pad_code(args.code) if args.code else None
    files = csv_files_to_process(start)
    if not files:
        print("No CSV files found to process")
        sys.exit(1)

    print(f"Files to process: {[os.path.basename(f) for f in files]}")
    for path in files:
        process_one(path)


if __name__ == "__main__":
    main()
