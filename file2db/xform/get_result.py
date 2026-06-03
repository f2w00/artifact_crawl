import json
import os

from method import rpc

DIR = os.path.dirname(__file__)
AUTOFILL_DIR = os.path.normpath(os.path.join(DIR, "..", "autofill"))

result = rpc("xform.get_result", {"task_id": "xform_relic", "limit": 200})
results = result["results"]

out_path = os.path.join(AUTOFILL_DIR, "xform_relic.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for item in results:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Saved {len(results)} items to {out_path}")
