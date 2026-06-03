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
BATCH_SIZE = 5000


def pad_code(raw: str) -> str:
    return raw.zfill(6)


def csv_files_since(start: str) -> list[str]:
    pattern = os.path.join(DIR, "*.csv")
    result = []
    for path in sorted(glob.glob(pattern)):
        fname = os.path.basename(path)
        code = fname.replace(".csv", "")
        if len(code) == 6 and code.isdigit() and code >= start:
            result.append(path)
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_to_pg.py <start_code>")
        print("Example: python import_to_pg.py 3    # reads 000003.csv, 000004.csv")
        sys.exit(1)

    start = pad_code(sys.argv[1])
    files = csv_files_since(start)
    if not files:
        print(f"No CSV files found starting from {start}")
        sys.exit(1)

    print(f"Reading: {[os.path.basename(f) for f in files]}")

    conn = psycopg2.connect(**DB_CONFIG)  # pyright: ignore[reportCallIssue, reportArgumentType]
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS artifacts_raw (
            id   BIGINT PRIMARY KEY,
            data JSONB NOT NULL
        )
    """)
    conn.commit()

    total = 0
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            batch = []
            count = 0
            for row in reader:
                raw_id = row["id"]
                pk = int(raw_id.lstrip("0") or "0")
                raw_data = {k: v for k, v in row.items() if k != "id"}
                batch.append((pk, json.dumps(raw_data, ensure_ascii=False)))
                count += 1

                if len(batch) >= BATCH_SIZE:
                    cur.executemany(
                        "INSERT INTO artifacts_raw (id, data) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                        batch,
                    )
                    conn.commit()
                    batch.clear()

            if batch:
                cur.executemany(
                    "INSERT INTO artifacts_raw (id, data) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                    batch,
                )
                conn.commit()

            print(f"  {os.path.basename(fpath)}: {count} rows")
            total += count

    cur.close()
    conn.close()
    print(f"Total: {total} rows inserted")


if __name__ == "__main__":
    main()
