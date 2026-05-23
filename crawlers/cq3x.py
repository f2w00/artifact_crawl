import csv
import hashlib
import hmac
import json
import os
import random
import re
import time
import traceback
from urllib.parse import urljoin

import requests

# ============ 全局配置 ============
MAX_PAGES = 5244
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output', '3gmuseum')
CSV_BATCH_SIZE = 10000
STATE_FILE = os.path.join(BASE_DIR, 'output', '3gmuseum', 'state.json')
BASE_URL = 'https://www.3gmuseum.cn'
API_URL = 'https://www.3gmuseum.cn/foreground-gateway/retrieval/intensify/search'

# 签名密钥
SIGN_KEY = "bxoj7fpdcz976m8lwpsvamzr009gfkt7"

# columnIds - 固定值（整数格式）
COLUMN_IDS = 5010106
# =================================

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.3gmuseum.cn/',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/json',
}


def create_nonce(length=6):
    """创建随机字符串"""
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def Vt(obj):
    """转换数据类型（对应 JS 中的 Vt 函数）"""
    result = {}
    for key, value in obj.items():
        if value is None or value == "":
            continue
        if isinstance(value, list) and len(value) == 0:
            continue
        if isinstance(value, dict) and len(value) == 0:
            continue
        if isinstance(value, bool) or isinstance(value, list):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = Vt(value)
        else:
            result[key] = str(value)
    return result


def Jt(obj):
    """递归排序对象键（对应 JS 中的 Jt 函数）"""
    if isinstance(obj, dict):
        return {k: Jt(v) for k, v in sorted(obj.items())}
    return obj


def encrypt_params(data, nonce, timestamp):
    """生成签名（对应 JS 中的 encryptParams 函数）"""
    n = Jt(Vt(data))
    json_str = json.dumps(n, separators=(',', ':'), ensure_ascii=False)
    hmac1 = hmac.new(
        SIGN_KEY.encode('utf-8'),
        json_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().lower()
    o = SIGN_KEY + nonce + str(timestamp) + hmac1
    signature = hmac.new(
        SIGN_KEY.encode('utf-8'),
        o.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def parse_json_field(value):
    """解析 JSON 字符串字段，返回 name 值或原值"""
    if not value or not isinstance(value, str):
        return value
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed.get('name', parsed.get('id', value))
        elif isinstance(parsed, list) and len(parsed) > 0:
            if isinstance(parsed[0], dict):
                return parsed[0].get('name', parsed[0].get('id', value))
            return str(parsed)
        return value
    except (json.JSONDecodeError, AttributeError):
        return value


def parse_lb_field(value):
    """解析 extend_field_lb 字段（图片信息）"""
    if not value or not isinstance(value, str):
        return "", ""
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list) and len(parsed) > 0:
            first = parsed[0]
            file_url = first.get('fileUrl', '')
            thumbnail_url = first.get('fileThumbnailUrl', '')
            if file_url:
                file_url = urljoin(BASE_URL, file_url)
            if thumbnail_url:
                thumbnail_url = urljoin(BASE_URL, thumbnail_url)
            return file_url, thumbnail_url
        return "", ""
    except (json.JSONDecodeError, AttributeError):
        return "", ""


def fetch_page(session, page, column_ids, wwmc="", years="全部", wytype="全部", level="全部"):
    """获取指定页的数据"""
    nonce = create_nonce()
    timestamp = int(time.time() * 1000)

    data = {
        "appId": 30059,
        "currentPage": page,
        "pageSize": 15,
        "enableParticiple": True,
        "columnIds": column_ids,
    }

    template_ext_field = []
    if years and years != "全部":
        template_ext_field.append({
            "extFieldKey": "extend_field_year",
            "extFieldValue": years
        })
    if wytype and wytype != "全部":
        template_ext_field.append({
            "extFieldKey": "extend_field_nameXS",
            "extFieldValue": wytype
        })
    if level and level != "全部":
        template_ext_field.append({
            "extFieldKey": "extend_field_level",
            "extFieldValue": level
        })

    if template_ext_field:
        data["templateExtField"] = template_ext_field
    if wwmc:
        data["titleWord"] = wwmc

    signature = encrypt_params(data, nonce, timestamp)
    url = f"{API_URL}?signature={signature}&nonce={nonce}&timestamp={timestamp}"

    response = session.post(url, json=data, timeout=30)
    response.encoding = 'utf-8'

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"请求失败，状态码: {response.status_code}")


def parse_items(result):
    """解析返回的数据，提取所有字段"""
    items = []
    if not result or "dataList" not in result:
        return items, 0, 0

    records = result.get("dataList", [])

    for record in records:
        item = {}

        # 基本字段
        item["newsId"] = record.get("newsId", "")
        item["title"] = record.get("title", "")
        item["contentType"] = record.get("contentType", "")
        item["source"] = record.get("source", "")
        item["synopsis"] = record.get("synopsis", "")
        item["publishTime"] = record.get("publishTime", "")

        # 列表图片
        list_img = record.get("listImg", [])
        if isinstance(list_img, list) and len(list_img) > 0:
            item["listImg"] = urljoin(BASE_URL, list_img[0])
        else:
            item["listImg"] = ""

        # 扩展字段 - 从 templateExtField 获取
        ext_fields = record.get("templateExtField", {})
        for key, value in ext_fields.items():
            # 跳过不需要的字段（用户不需要 extend_field_year 相关字段）
            if key in ("extend_field_year", "extend_field_years"):
                continue
            # 特殊处理图片字段 extend_field_lb
            if key == "extend_field_lb":
                file_url, thumbnail_url = parse_lb_field(value)
                item["extend_field_lb_url"] = file_url
                item["extend_field_lb_thumbnail"] = thumbnail_url
            else:
                # 尝试解析 JSON 字符串
                item[key] = parse_json_field(value)

        # 栏目信息
        news_column_list = record.get("newsColumnList", [])
        if isinstance(news_column_list, list) and len(news_column_list) > 0:
            column = news_column_list[0].get("column", {})
            item["columnId"] = column.get("id", "")
            item["columnName"] = column.get("name", "")

        items.append(item)

    total = result.get("totalSize", 0)
    current_page = result.get("currentPage", 1)
    page_size = result.get("pageSize", 15)
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return items, total, total_pages


def get_all_field_names(items):
    """获取所有字段名并排序"""
    field_names = set()
    for item in items:
        field_names.update(item.keys())
    # 定义字段顺序（不包含不需要的字段）
    priority_fields = [
        "newsId", "title", "extend_field_relic_no",
        "extend_field_nameXS", "extend_field_level", "extend_field_size",
        "extend_field_texture1", "extend_field_texture_type", "extend_field_texture_o_type",
        "extend_field_height", "extend_field_length", "extend_field_width",
        "extend_field_mass_range", "extend_field_quality",
        "extend_field_num", "extend_field_real_num",
        "extend_field_source", "extend_field_in_year", "extend_field_in_time",
        "extend_field_residue_grade", "extend_field_save_state",
        "extend_field_resStatus", "extend_field_old_name",
        "extend_field_lb_url", "extend_field_lb_thumbnail",
        "listImg",
        "columnId", "columnName", "contentType", "source", "synopsis", "publishTime"
    ]
    sorted_fields = [f for f in priority_fields if f in field_names]
    remaining = sorted(field_names - set(priority_fields))
    return sorted_fields + remaining


def map_field_name(field):
    """映射字段名到中文（可选）"""
    field_map = {
        "newsId": "ID",
        "title": "名称",
        "extend_field_relic_no": "文物编号",
        "extend_field_nameXS": "类型",
        "extend_field_level": "级别",
        "extend_field_size": "尺寸",
        "extend_field_height": "高度",
        "extend_field_length": "长度",
        "extend_field_width": "宽度",
        "extend_field_texture1": "质地",
        "extend_field_texture_type": "质地类型",
        "extend_field_texture_o_type": "质地大类",
        "extend_field_mass_range": "质量范围",
        "extend_field_quality": "质量",
        "extend_field_num": "数量单位",
        "extend_field_real_num": "实际数量",
        "extend_field_source": "来源",
        "extend_field_in_year": "入藏年份",
        "extend_field_in_time": "入藏时间",
        "extend_field_residue_grade": "完残程度",
        "extend_field_save_state": "保存状态",
        "extend_field_resStatus": "现状描述",
        "extend_field_old_name": "原名",
        "extend_field_lb_url": "图片链接",
        "extend_field_lb_thumbnail": "缩略图",
        "listImg": "列表图片",
        "columnId": "栏目ID",
        "columnName": "栏目名称",
        "contentType": "内容类型",
        "source": "来源",
        "synopsis": "简介",
        "publishTime": "发布时间",
    }
    return field_map.get(field, field)


def save_to_csv(items, csv_file, field_names, use_chinese_header=False):
    """保存数据到 CSV"""
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    file_exists = os.path.exists(csv_file)

    with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            if use_chinese_header:
                header = [map_field_name(field) for field in field_names]
            else:
                header = field_names
            writer.writerow(header)

        for item in items:
            row = [str(item.get(field, "")) for field in field_names]
            writer.writerow(row)


def load_state():
    """加载状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def save_state(state):
    """保存状态"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    os.makedirs(CSV_OUTPUT_FOLDER, exist_ok=True)

    # 初始化会话
    session = requests.Session()
    session.headers.update(headers)

    # 加载状态
    state = load_state()
    if state:
        print(f"发现存档，已爬至第 {state['page']-1} 页，累计 {state['total_items']} 条")
        start_page = state['page']
        csv_index = state['csv_index']
        csv_rows = state['csv_rows']
        total_items = state['total_items']
        all_field_names = state.get('field_names', None)
    else:
        print("未发现存档，从头开始")
        start_page = 1
        csv_index = 1
        csv_rows = 0
        total_items = 0
        all_field_names = None

    page = start_page
    fail_count = 0
    request_count = 0

    while page <= MAX_PAGES:
        print(f"正在爬取第 {page} 页...")

        try:
            result = fetch_page(session, page, COLUMN_IDS)
            items, total, total_pages = parse_items(result)

            if not items:
                print(f"第 {page} 页无数据，爬取完成")
                break

            # 更新字段名
            if all_field_names is None:
                all_field_names = get_all_field_names(items)
                print(f"字段列表 ({len(all_field_names)} 个): {all_field_names}")

            # 保存数据
            csv_file = f'{CSV_OUTPUT_FOLDER}/3gmuseum_{csv_index}.csv'
            save_to_csv(items, csv_file, all_field_names, use_chinese_header=True)
            csv_rows += len(items)
            total_items += len(items)

            # 检查 CSV 是否满
            if csv_rows >= CSV_BATCH_SIZE:
                csv_index += 1
                csv_rows = 0

            # 保存进度
            save_state({
                'page': page + 1,
                'csv_index': csv_index,
                'csv_rows': csv_rows,
                'total_items': total_items,
                'field_names': all_field_names
            })

            print(f"第 {page} 页完成，本页 {len(items)} 条数据，累计 {total_items} 条")
            print(f"  (总数: {total}，总页数: {total_pages})")

            time.sleep(random.uniform(1, 3))
            page += 1
            fail_count = 0
            request_count += 1

            if page > total_pages and total_pages > 0:
                print("已到达最后一页")
                break

            if request_count % 10 == 0:
                print(f"已完成 {request_count} 次请求，长时睡眠中...")
                time.sleep(random.uniform(60, 120))

        except Exception as e:
            print(f"第 {page} 页失败: {str(e)}")
            traceback.print_exc()
            fail_count += 1
            print(f"正在重试... (连续失败 {fail_count} 次)")
            if fail_count >= 3:
                print("连续失败3次，停止爬取")
                break
            time.sleep(30)
            continue

    print(f"完成！共 {total_items} 条藏品信息")


if __name__ == "__main__":
    main()
