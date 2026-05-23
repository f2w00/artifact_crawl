import csv
import json
import os
import random
import time
import traceback
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ============ 全局配置 ============
MAX_PAGES = 1114
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_FOLDER = os.path.join(BASE_DIR, 'output', 'henan_museum', 'images')
CSV_OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output', 'henan_museum')
CSV_BATCH_SIZE = 10000
STATE_FILE = os.path.join(BASE_DIR, 'output', 'henan_museum', 'state.json')
BASE_URL = 'https://www.chnmus.net'
LIST_PAGE_URL = 'https://www.chnmus.net/ch/collection/boutique/index.html'
# =================================

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.chnmus.net/ch/collection/boutique/index.html',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(CSV_OUTPUT_FOLDER, exist_ok=True)


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
    """获取指定页的HTML"""
    url = 'https://www.chnmus.net/ch/collection/boutique/index.html?pageIndex=%d&dictionaryValues=' % page
    response = session.get(url, timeout=30)
    response.encoding = 'utf-8'
    return response.text


def parse_items(html):
    """解析HTML提取文物信息"""
    soup = BeautifulSoup(html, 'lxml')
    items = []

    # 从表格视图中提取数据
    list_container = soup.select_one('#list-container')
    if not list_container:
        return items

    for item_elem in list_container.select('.table-list-item'):
        try:
            # 提取链接和名称
            link_elem = item_elem.select_one('a')
            name_elem = item_elem.select_one('.before-dot span')
            type_elem = item_elem.select_one('.pc-show.col-md-4.text-center span')
            era_elem = item_elem.select_one('.pc-show.col-md-3.text-right span')

            # 提取图片链接
            img_elem = item_elem.select_one('.hover-image img:last-child')
            img_url = img_elem['src'] if img_elem and 'src' in img_elem.attrs else ''

            name = name_elem['title'] if name_elem and 'title' in name_elem.attrs else (name_elem.text.strip() if name_elem else '')
            category = type_elem.text.strip() if type_elem else ''
            era = era_elem['title'] if era_elem and 'title' in era_elem.attrs else (era_elem.text.strip() if era_elem else '')

            # 处理图片链接
            if img_url:
                full_img_url = urljoin(BASE_URL, img_url)
            else:
                full_img_url = ''

            items.append({
                'name': name,
                'category': category,
                'era': era,
                'img_url': full_img_url
            })
        except Exception as e:
            print("解析条目失败: " + str(e))
            continue

    return items


# 初始化会话
session = requests.Session()
session.headers.update(header)

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
request_count = 0

while page <= MAX_PAGES:
    print("正在爬取第 %d 页..." % page)

    try:
        html = fetch_page(session, page)
        items = parse_items(html)

        if not items:
            print("第 %d 页无数据，爬取完成" % page)
            break

        for item in items:
            name = item['name']
            category = item['category']
            era = item['era']
            full_img_url = item['img_url']

            current_id = item_id
            item_id += 1

            # 写入 CSV
            csv_file = '%s/henan_museum_%d.csv' % (CSV_OUTPUT_FOLDER, csv_index)
            file_exists = os.path.exists(csv_file)
            with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists or csv_rows == 0:
                    writer.writerow(['ID', '名称', '类型', '年代', '图片链接'])
                writer.writerow([
                    current_id,
                    name,
                    category,
                    era,
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

        print("第 %d 页完成，本页 %d 条数据，累计 %d 条" % (page, len(items), item_id-1))
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
