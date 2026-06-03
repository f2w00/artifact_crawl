import csv
import json
import os
import sys
import time

from method import rpc

DIR = os.path.dirname(__file__)
STORE_DIR = os.path.normpath(os.path.join(DIR, "..", "..", "store"))
SKIP_COLS = {"image_url", "来源 URL"}
TASK_ID = "xform_relic"
BATCH_SIZE = 100
POLL_INTERVAL = 60


def record_path(idx):
    return os.path.join(STORE_DIR, f"record_{idx:06d}.json")


def load_record(idx):
    path = record_path(idx)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_record(idx, data):
    path = record_path(idx)
    with open(path, "w") as f:
        json.dump(data, f)


def wait_pipe_clear():
    while True:
        status = rpc("xform.get_status", {"task_id": TASK_ID})
        if status.get("pending_input", 0) <= BATCH_SIZE:
            break
        print(
            f"  pending_input={status.get('pending_input')} > {BATCH_SIZE}, waiting {POLL_INTERVAL}s..."
        )
        time.sleep(POLL_INTERVAL)


def process_file(idx):
    csv_path = os.path.join(STORE_DIR, f"{idx:06d}.csv")
    record = load_record(idx)

    if record and record.get("done"):
        print(f"Skip {idx:06d}.csv: already completed")
        return

    skip = record.get("row_offset", 0) if record else 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for _ in range(skip):
            next(reader)

        batch = []
        data_rows = skip
        for row in reader:
            row = {k: v for k, v in row.items() if k not in SKIP_COLS}
            if "relic_id" in row:
                row["relic_id"] = int(row["relic_id"])
            batch.append(row)

            if len(batch) >= BATCH_SIZE:
                wait_pipe_clear()
                rpc("xform.append", {"task_id": TASK_ID, "data": batch})
                data_rows += len(batch)
                save_record(idx, {"row_offset": data_rows})
                print(f"  Appended {len(batch)} rows (offset={data_rows})")
                batch = []
                time.sleep(POLL_INTERVAL)

        if batch:
            wait_pipe_clear()
            rpc("xform.append", {"task_id": TASK_ID, "data": batch})
            data_rows += len(batch)
            print(f"  Appended {len(batch)} rows (offset={data_rows})")

        save_record(idx, {"row_offset": data_rows, "done": True})
        print(f"Done {idx:06d}.csv ({data_rows} rows)")


def main(max_index):
    for idx in range(max_index + 1):
        csv_path = os.path.join(STORE_DIR, f"{idx:06d}.csv")
        if not os.path.exists(csv_path):
            print(f"Skip {idx:06d}.csv: not found")
            continue
        process_file(idx)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <max_index>")
        sys.exit(1)
    main(int(sys.argv[1]))
