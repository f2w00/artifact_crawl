import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(BASE_DIR, "store")

COLUMN_MAP = {
    "图片 URL": "image_url",
    "图片URL": "image_url",
    "图片链接": "image_url",
    "图片地址": "image_url",
}


def normalize_csv(csv_path):
    fname = os.path.basename(csv_path)
    rows = []
    new_headers = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        old_headers = reader.fieldnames

        has_image_col = False
        for h in old_headers:
            if h in COLUMN_MAP:
                new_headers.append(COLUMN_MAP[h])
                has_image_col = True
            else:
                new_headers.append(h)

        if not has_image_col:
            print(f"  {fname}: 跳过 (无图片列)")
            return

        for row in reader:
            new_row = {}
            for old_h, new_h in zip(old_headers, new_headers):
                new_row[new_h] = row.get(old_h, "")
            rows.append(new_row)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_headers)
        writer.writeheader()
        writer.writerows(rows)

    changes = []
    for old_h, new_h in zip(old_headers, new_headers):
        if old_h != new_h:
            changes.append(f"{repr(old_h)} → {repr(new_h)}")

    print(f"  {fname}: {len(rows)} rows, {', '.join(changes)}")


def main():
    print("统一 store/ 下 CSV 图片列名...\n")

    csv_files = sorted(
        os.path.join(STORE_DIR, f) for f in os.listdir(STORE_DIR) if f.endswith(".csv")
    )

    if not csv_files:
        print("未找到 CSV 文件")
        sys.exit(1)

    for csv_path in csv_files:
        normalize_csv(csv_path)

    print("\n完成.")


if __name__ == "__main__":
    main()
