import requests


def rpc(method, params):
    return requests.post(
        "http://10.15.22.91:8848/rpc",
        json={"jsonrpc": "2.0", "method": method, "params": params, "id": "req"},
    ).json()


# 创建配置
rpc(
    "profile.set",
    {
        "profile_id": "demo",
        "llm": {
            "base_url": "http://172.18.20.44:30059/v1",
            "api_key": "sk_4f9d72a58c1e0b367890abcd1234ef567890abcdef123456",
            "model": "kg-assist",
            "timeout_seconds": 300,
        },
    },
)

# rpc(
#     "profile.set",
#     {
#         "profile_id": "alidsv4",
#         "llm": {
#             "base_url": "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
#             "api_key": "sk-sp-djI.tVlCWlHslPhAR43rqQOSRcm0Sb9YAKPcxJKF8e9V_n4Xua8U-JWxUconQktQAMknBue50pqTDqlneqmmz7N1SaiSMAmh0dzbh9i6y803NQ4CTFWjhWg9SCMCe86MU_9e.MEUCIQDMTF9qRLnK-Gq9YztwVUZ-LKypcmmoof0GKLNP6s0hvQIgeEn9ALlM3u8jAi6Vmc5Rg6zw7BxGqryOQ9BN5AQLpbM",
#             "model": "deepseek-v4-flash",
#             "timeout_seconds": 300,
#         },
#     },
# )
