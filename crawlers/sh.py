import csv
import json
import os
import random
import time
import traceback
from urllib.parse import urljoin

import requests

# ============ 全局配置 ============
MAX_PAGES = 3000
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_FOLDER = os.path.join(BASE_DIR, 'output', 'shanghai_museum', 'images')
CSV_OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output', 'shanghai_museum')
CSV_BATCH_SIZE = 10000
STATE_FILE = os.path.join(BASE_DIR, 'output', 'shanghai_museum', 'state.json')
BASE_URL = 'https://www.shanghaimuseum.net/mu/'
API_URL = 'https://www.shanghaimuseum.net/mu/frontend/pg/collection/search-antique'
LIST_PAGE_URL = 'https://www.shanghaimuseum.net/mu/frontend/pg/lib1/antique'
# =================================

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.shanghaimuseum.net/mu/frontend/pg/lib1/antique',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/json',
}

os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(CSV_OUTPUT_FOLDER, exist_ok=True)

# 所有文物类型（从目标URL提取）
LIB_TYPES = [
    "LIB_TYPE_0001", "LIB_TYPE_0002", "LIB_TYPE_0003", "LIB_TYPE_0004", "LIB_TYPE_0005",
    "LIB_TYPE_0006", "LIB_TYPE_0007", "LIB_TYPE_0008", "LIB_TYPE_0009", "LIB_TYPE_0010",
    "LIB_TYPE_0011", "LIB_TYPE_0012", "LIB_TYPE_0013", "LIB_TYPE_0014", "LIB_TYPE_0015",
    "LIB_TYPE_0016", "LIB_TYPE_0017", "LIB_TYPE_0018", "LIB_TYPE_0019",
    "LIB_TYPE_0020/0001", "LIB_TYPE_0020/0002",
    "LIB_TYPE_0021/0001", "LIB_TYPE_0021/0002", "LIB_TYPE_0021/0003", "LIB_TYPE_0021/0004",
    "LIB_TYPE_0022/0001", "LIB_TYPE_0022/0002",
    "LIB_TYPE_0023/0001", "LIB_TYPE_0023/0002", "LIB_TYPE_0023/0003", "LIB_TYPE_0023/0004",
    "LIB_TYPE_0025/0001", "LIB_TYPE_0025/0002",
    "LIB_TYPE_0024/0001", "LIB_TYPE_0024/0002", "LIB_TYPE_0024/0003", "LIB_TYPE_0024/0004", "LIB_TYPE_0024/0005"
]


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return {
                'page': state.get('page', 1),
                'item_id': state.get('item_id', 1),
                'csv_index': state.get('csv_index', 1),
                'csv_rows': state.get('csv_rows', 0)
            }
    return None


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'page': state['page'],
            'item_id': state['item_id'],
            'csv_index': state['csv_index'],
            'csv_rows': state['csv_rows']
        }, f, ensure_ascii=False, indent=2)


def fetch_page(session, page):
    """获取指定页的数据"""
    payload = {
        'params': {
            'langCode': 'CATALOG_CHINESE',
            'libTypes': LIB_TYPES,
            'libAges': [],
            'searchText': '',
            'libTypeSort': '',
            'libAgeSort': '',
            'libOnlyShowPic': ''
        },
        'page': page,
        'limit': 20
    }

    response = session.post(API_URL, json=payload, timeout=30)
    return response.json()


# 初始化会话
session = requests.Session()
session.headers.update(header)

# 先访问列表页获取Cookie
print("正在访问列表页初始化会话...")
try:
    session.get(LIST_PAGE_URL, timeout=30)
    print("会话初始化成功")
except Exception as e:
    print("会话初始化失败: " + str(e))

# 加载状态
state = load_state()
if state:
    print("发现存档，已爬至第 %d 页，当前 ID: %d" % (state['page']-1, state['item_id']))
    start_page = state['page']
    item_id = state['item_id']
    csv_index = state['csv_index']
    csv_rows = state['csv_rows']
else:
    print("未发现存档，从头开始")
    start_page = 1
    item_id = 1
    csv_index = 1
    csv_rows = 0

page = start_page
fail_count = 0
total_count = 0
request_count = 0  # 添加请求计数器

while page <= MAX_PAGES:
    print("正在爬取第 %d 页..." % page)

    try:
        result = fetch_page(session, page)

        if result.get('code') != 0:
            print("第 %d 页返回错误: %s" % (page, result.get('msg', '未知错误')))
            fail_count += 1
            if fail_count >= 3:
                print("连续失败3次，停止爬取")
                break
            time.sleep(5)
            continue

        data = result.get('data', [])
        if not data:
            print("第 %d 页无数据，爬取完成" % page)
            break

        # 首次获取总数
        if total_count == 0 and 'count' in result:
            total_count = result['count']
            print("总数据量: %d" % total_count)

        for item in data:
            name = item.get('name', '')
            pic_path = item.get('picPath', '')
            intra_age_code = item.get('intraAgeCode', '')
            antique_type = item.get('antiqueType1', {})
            category = antique_type.get('entryItemName', '') if antique_type else ''

            # 处理图片链接
            if pic_path:
                full_img_url = urljoin(BASE_URL, pic_path)
            else:
                full_img_url = ''

            current_id = item_id
            item_id += 1

            # 写入 CSV
            csv_file = '%s/shanghai_museum_%d.csv' % (CSV_OUTPUT_FOLDER, csv_index)
            file_exists = os.path.exists(csv_file)
            with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists or csv_rows == 0:
                    writer.writerow(['ID', '名称', '时代', '类别', '图片链接'])
                writer.writerow([
                    current_id,
                    name,
                    intra_age_code,
                    category,
                    full_img_url
                ])
            csv_rows += 1

            # 检查 CSV 是否满
            if csv_rows >= CSV_BATCH_SIZE:
                csv_index += 1
                csv_rows = 0

        # 保存进度
        save_state({
            'page': page + 1,
            'item_id': item_id,
            'csv_index': csv_index,
            'csv_rows': csv_rows
        })

        print("第 %d 页完成，本页 %d 条数据，累计 %d 条" % (page, len(data), item_id-1))
        time.sleep(random.uniform(1, 3))
        page += 1
        fail_count = 0
        request_count += 1

        # 每10次请求后睡眠更长时间
        if request_count % 10 == 0:
            print("已完成 %d 次请求，长时睡眠中..." % request_count)
            time.sleep(random.uniform(300, 600))

    except Exception as e:
        error_msg = traceback.format_exc()
        print("第 %d 页失败: %s" % (page, str(e)))
        fail_count += 1
        print("第 %d 页请求失败，正在重试... (连续失败 %d 次)" % (page, fail_count))
        if fail_count >= 3:
            print("连续失败3次，停止爬取")
            break
        time.sleep(2500)
        continue

print("完成！共 %d 条藏品信息" % (item_id-1))
