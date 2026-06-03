import csv
import glob
import json
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = dict(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dbname=os.getenv("DB_NAME"),
)

DIR = os.path.dirname(__file__)
STORE_DIR = os.path.join(DIR, "..", "store")
MAPPINGS_DIR = os.path.join(DIR, "mappings")
TARGETS_FILE = os.path.join(DIR, "targets.json")
BATCH_SIZE = 5000
TABLE_NAME = "relic_raw"


def load_all_targets() -> list[str]:
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        return list(json.load(f).keys())


def load_mappings() -> dict:
    result = {}
    for fpath in sorted(glob.glob(os.path.join(MAPPINGS_DIR, "*_mapping.json"))):
        fname = os.path.basename(fpath)
        code = fname.replace("_mapping.json", "")
        with open(fpath, "r", encoding="utf-8") as f:
            raw = json.load(f)
        content = raw.get("result", {})
        mapping = content.get("mapping", {})
        unmapped_source = content.get("unmapped_source") or []
        unfilled_target = content.get("unfilled_target", [])
        # 将 mapping 的值从 list 转为第一个元素
        flat_mapping = {tgt: vals[0] if vals else None for tgt, vals in mapping.items()}
        result[code] = {
            "mapping": flat_mapping,
            "unmapped_source": unmapped_source,
            "unfilled_target": unfilled_target,
        }
    return result


def csv_files_since(start: str, available_codes: set[str]) -> list[str]:
    result = []
    for code in sorted(available_codes):
        if code >= start:
            result.append(code)
    return result


def transform_row(row: dict, mapping_info: dict, all_targets: list[str]) -> tuple:
    flat_mapping = mapping_info["mapping"]
    unmapped_source_cols = mapping_info["unmapped_source"]
    unfilled_target = mapping_info["unfilled_target"]

    relic_id_raw = row.get("relic_id", "0")
    relic_id = int(relic_id_raw.lstrip("0") or "0")

    data = {}
    for target in all_targets:
        if target in flat_mapping:
            source_col = flat_mapping[target]
            if source_col is not None:
                val = row.get(source_col, None)
                if val == "":
                    val = None
                data[target] = val
            else:
                data[target] = None
        elif target in unfilled_target:
            data[target] = None
        else:
            data[target] = None

    unmapped = {}
    for col in unmapped_source_cols:
        unmapped[col] = row.get(col, "")
        if unmapped[col] == "":
            unmapped[col] = None

    return relic_id, data, unmapped


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {os.path.basename(__file__)} <start_code>")
        print(
            "Example: python import_mapped_to_pg.py 3   # processes 000003.csv onwards"
        )
        sys.exit(1)

    all_targets = load_all_targets()
    all_mappings = load_mappings()
    available_codes = set(all_mappings.keys())

    start = sys.argv[1].zfill(6)
    codes_to_process = csv_files_since(start, available_codes)

    if not codes_to_process:
        print(f"No mapping files found starting from code {start}")
        sys.exit(1)

    print(f"Processing codes: {codes_to_process}")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            relic_id        BIGINT PRIMARY KEY,
            data            JSONB NOT NULL,
            unmapped_source JSONB,
            ext_info        JSONB DEFAULT '{{}}'
        )
    """)
    conn.commit()

    total = 0
    for code in codes_to_process:
        csv_path = os.path.join(STORE_DIR, f"{code}.csv")
        if not os.path.exists(csv_path):
            print(f"  Skipping {code}: CSV file not found ({csv_path})")
            continue

        mapping_info = all_mappings[code]
        print(f"  Processing {code}.csv with mapping...")

        batch = []
        count = 0

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                relic_id, data, unmapped = transform_row(row, mapping_info, all_targets)
                batch.append(
                    (
                        relic_id,
                        json.dumps(data, ensure_ascii=False),
                        json.dumps(unmapped, ensure_ascii=False) if unmapped else None,
                    )
                )
                count += 1

                if len(batch) >= BATCH_SIZE:
                    cur.executemany(
                        f"INSERT INTO {TABLE_NAME} (relic_id, data, unmapped_source, ext_info) "
                        "VALUES (%s, %s, %s, %s) ON CONFLICT (relic_id) DO NOTHING",
                        [(*row, "{}") for row in batch],
                    )
                    conn.commit()
                    batch.clear()

            if batch:
                cur.executemany(
                    f"INSERT INTO {TABLE_NAME} (relic_id, data, unmapped_source, ext_info) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (relic_id) DO NOTHING",
                    [(*row, "{}") for row in batch],
                )
                conn.commit()
                batch.clear()

        print(f"    {code}.csv: {count} rows")
        total += count

    cur.close()
    conn.close()
    print(f"\nTotal: {total} rows inserted into {TABLE_NAME}")


if __name__ == "__main__":
    main()
