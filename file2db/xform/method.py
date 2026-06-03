import os

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

BASE_URL = os.getenv("BASE_URL", "http://localhost:8848/rpc")


def rpc(method, params, req_id="req"):
    """发送 JSON-RPC 请求"""
    resp = requests.post(
        BASE_URL,
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": req_id},
    )
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC Error: {data['error']}")
    return data["result"]
