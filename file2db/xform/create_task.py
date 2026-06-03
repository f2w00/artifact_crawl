from method import rpc

# ======================== 1. 提交任务 ========================

result = rpc(
    "xform.submit",
    {
        "task_id": "xform_relic",
        "profile_id": "demo",
        "targets_example": [
            {
                "relic_id": 800000001,
                "relic_name": "唐三彩骆驼载乐俑",
                "relic_big_type": "陶器",
                "relic_shape_type": "俑",
                "relic_usage": "明器",
                "main_material": "陶",
                "relic_source": "考古发掘",
                "relic_status": "完整",
                "relic_brief": "骆驼昂首立于方形底板上，驼背上有胡人乐俑七尊，手持琵琶、筚篥等乐器",
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
                "craft_school": "巩县窑流派",
                "related_person_name": "李世民",
                "person_relation_type": "宫廷御用",
                "person_relation_desc": "该俑出土地邻近昭陵，可能与太宗李世民陵寝陪葬制度有关",
            }
        ],
        "primary_key": "relic_id",
        "pool_size": 30,
        "max_retries": 2,
        "ttl_hours": 24,
    },
)
task_id = result["task_id"]
print(task_id)
