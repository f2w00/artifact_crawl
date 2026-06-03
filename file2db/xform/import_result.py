import json
import os
import time

import psycopg2
from dotenv import load_dotenv
from method import rpc

load_dotenv()

DIR = os.path.dirname(__file__)
TABLE_NAME = "relic_standard"
POLL_INTERVAL = 120
BATCH_LIMIT = 2000
ERROR_LOG = os.path.join(DIR, "errors.jsonl")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    dbname=os.getenv("DB_NAME"),
)
cur = conn.cursor()

cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        relic_id        BIGINT PRIMARY KEY,
        data            JSONB NOT NULL,
        ext_info        JSONB DEFAULT NULL
    )
""")
conn.commit()

total = 0

while True:
    try:
        result = rpc(
            "xform.get_result", {"task_id": "xform_relic", "limit": BATCH_LIMIT}
        )
        results = result["results"]
        pending = result["pending_output"]
        status = result.get("status")
        errors = result.get("errors", [])
        if errors:
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
                for err in errors:
                    f.write(json.dumps(err, ensure_ascii=False) + "\n")
        skip = True if int(pending) > BATCH_LIMIT else False
    except Exception as e:
        print(f"RPC error: {e}")
        time.sleep(POLL_INTERVAL)
        continue

    if not results:
        if status == "failed":
            print(f"Task status is '{status}', exiting.")
            break
        if status == "closed" and pending == 0:
            print(f"Task status is '{status}', exiting.")
            break
        print(f"No results, waiting {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
        continue

    batch = []
    for item in results:
        relic_id_raw = item.get("relic_id", "0")
        if isinstance(relic_id_raw, str):
            relic_id = int(relic_id_raw.lstrip("0") or "0")
        else:
            relic_id = int(relic_id_raw)
        batch.append((relic_id, json.dumps(item, ensure_ascii=False)))

    cur.executemany(
        f"INSERT INTO {TABLE_NAME} (relic_id, data) "
        "VALUES (%s, %s) ON CONFLICT (relic_id) DO NOTHING",
        batch,
    )
    conn.commit()
    total += len(batch)
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] Inserted {len(batch)} rows (total: {total})")

    if status == "failed":
        print(f"Task status is '{status}', exiting.")
        break
    if status == "closed" and pending == 0:
        print(f"Task status is '{status}', exiting.")
        break

    if not skip:
        time.sleep(POLL_INTERVAL)
