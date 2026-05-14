import csv
import json
import os
import random
import time
import traceback
from urllib.parse import urljoin

import requests

# ============ 全局配置 ============
MAX_PAGES = 9301
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output', 'dpm_museum')
CSV_BATCH_SIZE = 10000
STATE_FILE = os.path.join(OUTPUT_FOLDER, 'state.json')

# API端点
BASE_URL = 'https://zm-digicol.dpm.org.cn'
API_URL = 'https://zm-digicol.dpm.org.cn/cultural/queryList'
DETAIL_BASE_URL = 'http://digicol.dpm.org.cn/cultural/detail?id='

# 目标分类ID列表（从URL提取）
CATEGORIES = ["17", "16", "1", "5", "15", "9", "10", "21", "14", "6", "4", "3", "23", "7", "20", "12", "11", "19", "22", "2", "18", "25", "24", "8", "13"]
# =================================

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://zm-digicol.dpm.org.cn/cultural/list',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
}

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def load_state():
    """加载爬取进度"""
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
    """保存爬取进度"""
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
        'page': page,
        'pageSize': 200,
        'keyWord': '',
        'cateList': ','.join(CATEGORIES),
        'dynastys': '',
        'sortType': '',
        'hasMhj': '0',
        'hasDbg': '0',
        'ranNum': random.random()
    }

    response = session.post(API_URL, data=payload, timeout=30)
    return response.json()


# 初始化会话
session = requests.Session()
session.headers.update(headers)

# 先访问首页获取必要Cookie
print("正在访问首页初始化会话...")
try:
    session.get('https://zm-digicol.dpm.org.cn/cultural/list', timeout=30)
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
request_count = 0

while page <= MAX_PAGES:
    print("正在爬取第 %d 页..." % page)

    try:
        result = fetch_page(session, page)

        rows = result.get('rows', [])
        if not rows:
            print("第 %d 页无数据，爬取完成" % page)
            break

        # 首次获取总数
        if total_count == 0 and 'recordcount' in result:
            total_count = result['recordcount']
            print("总数据量: %d" % total_count)
            print("预计总页数: %d" % ((total_count + 199) // 200))

        for item in rows:
            uuid = item.get('uuid', '')
            name = item.get('name', '')
            cultural_relic_no = item.get('culturalRelicNo', '')
            dynasty_name = item.get('dynastyName', '') or ''
            category_name = item.get('suggestCategoryName', '') or ''
            has_image = item.get('hasImage', 0)
            mhj_url = item.get('mhjUrl', '') or ''
            dbg_url = item.get('dbgUrl', '') or ''

            # 构造详情页链接
            detail_url = DETAIL_BASE_URL + uuid + '&source=6' if uuid else ''

            # 构造图片链接（如果有）
            image_url = ''
            if has_image == 1:
                # 详情页才有完整图片，这里只记录有图片的标记
                image_url = detail_url  # 指引到详情页查看图片

            current_id = item_id
            item_id += 1

            # 写入 CSV
            csv_file = os.path.join(OUTPUT_FOLDER, 'dpm_museum_%d.csv' % csv_index)
            file_exists = os.path.exists(csv_file)
            with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists or csv_rows == 0:
                    writer.writerow(['ID', '文物号', '文物名称', '年代', '类别', '详情页链接', '全景图链接', '三维模型链接', '是否有影像'])
                writer.writerow([
                    current_id,
                    cultural_relic_no,
                    name,
                    dynasty_name,
                    category_name,
                    detail_url,
                    mhj_url,
                    dbg_url,
                    '是' if has_image == 1 else '否'
                ])
            csv_rows += 1

            # 检查 CSV 是否满
            if csv_rows >= CSV_BATCH_SIZE:
                csv_index += 1
                csv_rows = 0
                print("创建新的CSV文件: %d" % csv_index)

        # 保存进度
        save_state({
            'page': page + 1,
            'item_id': item_id,
            'csv_index': csv_index,
            'csv_rows': csv_rows
        })

        print("第 %d 页完成，本页 %d 条数据，累计 %d 条" % (page, len(rows), item_id-1))

        # 随机延迟，避免被反爬
        sleep_time = random.uniform(1, 3)
        time.sleep(sleep_time)
        page += 1
        fail_count = 0
        request_count += 1

        # 每20次请求后长时睡眠
        if request_count % 20 == 0:
            long_sleep = random.uniform(30, 60)
            print("已完成 %d 次请求，长时睡眠 %.0f 秒..." % (request_count, long_sleep))
            time.sleep(long_sleep)

    except Exception as e:
        fail_count += 1
        print("第 %d 页请求失败: %s" % (page, str(e)))
        if fail_count >= 3:
            print("连续失败3次，停止爬取")
            break
        print("等待25秒后重试...")
        time.sleep(25)
        continue

print("完成！共爬取 %d 条藏品信息" % (item_id-1))
print("输出目录: %s" % OUTPUT_FOLDER)
