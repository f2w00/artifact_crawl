import argparse
import csv
import json
import os

DIR = os.path.dirname(__file__)
STORE_DIR = os.path.normpath(os.path.join(DIR, "..", "store"))

TARGETS_EXAMPLE = [
    {
        "relic_id": "00000100000001",
        "relic_name": "唐三彩骆驼载乐俑",
        "relic_big_type": "陶器",
        "relic_shape_type": "俑",
        "relic_usage": "明器",
        "main_material": "陶",
        "museum_name": "中国国家博物馆",
        "img_url": "https://example.com/images/tang_sancai_camel.jpg",
        "relic_source": "考古发掘",
        "relic_status": "完整",
        "relic_brief": "骆驼昂首立于方形底板上，驼背上有胡人乐俑七尊，手持琵琶、筚篥等乐器，中间一女俑翩翩起舞，造型生动，釉色绚丽，是唐三彩中罕见的精品。",
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
        "craft_school": "唐代巩县窑",
        "related_person_name": "李世民",
        "person_relation_type": "宫廷御用",
        "person_relation_desc": "该俑出土地邻近昭陵，可能与太宗李世民陵寝陪葬制度有关",
    }
]


def pad_code(raw: str) -> str:
    return raw.zfill(6)


def main():
    parser = argparse.ArgumentParser(description="Generate transform example from CSV")
    parser.add_argument("code", help="Museum code (e.g. 1 -> 000001.csv)")
    args = parser.parse_args()

    csv_path = os.path.join(STORE_DIR, f"{pad_code(args.code)}.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found")
        return

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= 2:
                break
            rows.append(row)

    if not rows:
        print("Error: CSV is empty")
        return

    payload = {
        "profile_id": "demo",
        "data": rows,
        "targets_example": TARGETS_EXAMPLE,
    }

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
