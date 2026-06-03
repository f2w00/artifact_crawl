import argparse
import csv
import json
import os
import time

import requests

DIR = os.path.dirname(__file__)
AUTOFILL_DIR = DIR
STORE_DIR = os.path.normpath(os.path.join(DIR, "..", "..", "store"))

TARGETS_EXAMPLE = [
    {
        "relic_id": 800000001,
        "relic_name": "唐三彩骆驼载乐俑",
        "relic_big_type": "陶器",
        "relic_shape_type": "俑",
        "relic_usage": "明器",
        "main_material": "陶",
        "relic_source": "考古发掘",
        "relic_status": "完整",
        "relic_brief": "骆驼昂首立于方形底板上，驼背上有胡人乐俑七尊，手持琵琶、筚篥等乐器",
        "dynasty": "唐",
        "history_stage": "盛唐",
        "unearthed_address": "陕西省-西安市-长安区-唐墓",
        "site_type": "帝王墓葬",
        "culture_belong": "中原文化",
        "main_pattern": "骆驼纹、胡人纹",
        "pattern_make_craft": "釉彩绘制",
        "pattern_position": "器身",
        "pattern_meaning": "丝绸之路中外文化交流的象征",
        "total_craft": "拉坯成型、三彩釉烧制",
        "craft_school": "巩县窑流派",
        "related_person_name": "李世民",
        "person_relation_type": "宫廷御用",
        "person_relation_desc": "该俑出土地邻近昭陵，可能与太宗李世民陵寝陪葬制度有关",
    }
]


def rpc(method, params):
    return requests.post(
        "http://localhost:8848/rpc",
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": "req"},
    ).json()


def pad_code(raw: str) -> str:
    return raw.zfill(6)


def main():
    parser = argparse.ArgumentParser(description="Generate transform example from CSV")
    parser.add_argument("code", help="Museum code (e.g. 1 -> 000001.csv)")
    parser.add_argument(
        "profile_id", nargs="?", default="demo", help="Profile ID (default: demo)"
    )
    args = parser.parse_args()

    csv_path = os.path.join(STORE_DIR, f"{pad_code(args.code)}.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        return

    skip_cols = {"image_url", "来源 URL"}

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= 1:
                break
            rows.append({k: v for k, v in row.items() if k not in skip_cols})

    if not rows:
        print("Error: CSV is empty")
        return

    payload = {
        "profile_id": args.profile_id,
        "data": rows,
        "targets_example": TARGETS_EXAMPLE,
        "primary_key": "relic_id",
    }

    start = time.time()
    resp = rpc("kgc.autofill", payload)
    elapsed = time.time() - start
    print(f"Elapsed: {elapsed:.2f}s")
    print(json.dumps(resp, ensure_ascii=False, indent=2))

    if "result" not in resp or "data" not in resp["result"]:
        print("FAILED")
        print(f"Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")
        return

    out_path = os.path.join(AUTOFILL_DIR, f"{args.code}_{args.profile_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
