import requests


def rpc(method, params):
    return requests.post(
        "http://localhost:8848/rpc",
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": "req"},
    ).json()


# 创建配置
rpc(
    "profile.set",
    {
        "profile_id": "demo",
        "llm": {
            "base_url": "http://localhost:8000/v1",
            "api_key": "sk-xxx",
            "model": "qwen2.5",
        },
    },
)

# 生成字段映射
resp = rpc(
    "mapping.field",
    {
        "profile_id": "demo",
        "example": {"title": "青花瓷瓶", "era": "明代"},
        "target_fields": ["name", "dynasty"],
    },
)
mapping = resp["result"]["mapping"]

# 内容映射（先设置目标值）
rpc(
    "mapping.content.targets.set",
    {"profile_id": "demo", "topic": "dynasty", "targets": ["唐", "宋", "明", "清"]},
)

# 再查询映射（不传 targets，从存储读取）
resp = rpc(
    "mapping.content",
    {"profile_id": "demo", "topic": "dynasty", "values": ["唐朝", "宋朝"]},
)
content_mapping = resp["result"]["mapping"]

# 或直接传入 targets（会隐式持久化）
resp = rpc(
    "mapping.content",
    {
        "profile_id": "demo",
        "topic": "dynasty",
        "values": ["唐朝", "宋朝"],
        "targets": ["唐", "宋", "明", "清"],
    },
)
content_mapping = resp["result"]["mapping"]

# 批量应用
rows = [{"title": "青花瓷瓶", "era": "明代"}, {"title": "铜鼎", "era": "商代"}]
output = [{tgt: row[src] for src, tgt in mapping.items()} for row in rows]
