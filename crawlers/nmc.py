import csv
import json
import os
import random
import re
import time
import traceback
from urllib.parse import quote

import requests

# ============ 全局配置 ============
MAX_PAGES = 400
IMAGES_FOLDER = 'output/nmc/images'
CSV_OUTPUT_FOLDER = 'output/nmc'
CSV_BATCH_SIZE = 12000
DOWNLOAD_BATCH = 1000
STATE_FILE = 'output/nmc/state.json'
# =================================

header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Referer': 'https://www.chnmuseum.cn/',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'X-Requested-With': 'XMLHttpRequest',
}
BASE_URL = 'https://www.chnmuseum.cn'

os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(CSV_OUTPUT_FOLDER, exist_ok=True)
# img_url_template2=f"{BASE_URL}/portals/0/web/zt/cangpin{quote(img, safe='/')}"
# img_url_template=f"{BASE_URL}/portals/0/web/zt/cangpin{quote(img, safe='/')}"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return {
                'page': state.get('page', 1),
                'img_id': state.get('img_id', 1),
                'csv_index': state.get('csv_index', 1),
                'csv_rows': state.get('csv_rows', 0)
            }
    return None


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'page': state['page'],
            'img_id': state['img_id'],
            'csv_index': state['csv_index'],
            'csv_rows': state['csv_rows']
        }, f, ensure_ascii=False, indent=2)


state = load_state()
if state:
    print(f"发现存档，已爬至第 {state['page']-1} 页，当前 ID: {state['img_id']}")
    start_page = state['page']
    img_id = state['img_id']
    csv_index = state['csv_index']
    csv_rows = state['csv_rows']
else:
    print("未发现存档，从头开始")
    start_page = 1
    img_id = 1
    csv_index = 1
    csv_rows = 0

downloaded_count = 0
page=start_page
fail_count=0
# for page in range(start_page, MAX_PAGES + 1):
while page<=MAX_PAGES:

    url = f'https://www.chnmuseum.cn/portals/0/web/zt/cangpin/json/cangpin/cangpin_{page}.js?_={int(time.time() * 1000 + random.randint(0, 999))}'

    print(f"正在爬取第 {page}/{MAX_PAGES} 页...")

    try:
        response = requests.get(url, headers=header, timeout=30)
        response_text = response.text.strip()
        if not response_text:
            print(f"第 {page} 页无数据，停止")
            break
        # 使用正则表达式提取等号后的JSON内容
        match = re.search(r'=(.+)$', response_text)
        if match:
            json_str = match.group(1).rstrip().rstrip(';')
            my_data = json.loads(json_str).get(f"objs_{page}", [])
        else:
            print(f"无法解析第 {page} 页的响应内容: {response_text}")
            my_data = []

        if not my_data:
            print(f"第 {page} 页无数据，停止")
            break

        for item in my_data:
            rname = item.get('rname', '')
            rera = item.get('rera', '')
            img = item.get('image', '')
            item_number=item.get('rnum', '')

            if img:
                # 将反斜杠替换为正斜杠，并归一化路径
                img = img.replace('\\', '/')

                # 如果img不是以/开头，添加一个/
                if not img.startswith('/'):
                    img = '/' + img

                # 拼接完整URL（不再使用quote，因为img已经是正确格式的路径）
                # 或者继续使用quote但确保路径正确
                full_img_url = f"{BASE_URL}/portals/0/web/zt/cangpin{quote(img, safe='/')}"
                current_id = img_id
                img_id += 1

                # 写入 CSV
                csv_file = f'{CSV_OUTPUT_FOLDER}/nmc_{csv_index}.csv'
                file_exists = os.path.exists(csv_file)
                with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    if not file_exists or csv_rows == 0:
                        writer.writerow(['ID', '名称', '年代', '编号', '图片地址'])
                    writer.writerow([
                        current_id,
                        rname,
                        rera,
                        item_number,
                        full_img_url
                    ])
                csv_rows += 1

                # 下载图片
                # try:
                #     img_response = requests.get(full_img_url, timeout=30)
                #     if 'image' in img_response.headers.get('Content-Type', ''):
                #         with open(f'{IMAGES_FOLDER}/{current_id}.jpg', 'wb') as f:
                #             f.write(img_response.content)
                #         downloaded_count += 1
                #         # 每张图片下载后随机短暂停顿
                #         time.sleep(random.uniform(0.5, 1))
                #         # Sleep every 100 downloaded images
                #         if downloaded_count % 100 == 0:
                #             time.sleep(random.uniform(0.5, 1.5))
                # except Exception as e:
                #     print(f"下载失败: {full_img_url}, {e}")
                #     # 即使下载失败也添加短暂停顿以避免过快请求
                #     time.sleep(random.uniform(0.1, 0.5))

                # 检查 CSV 是否满
                if csv_rows >= CSV_BATCH_SIZE:
                    csv_index += 1
                    csv_rows = 0

        save_state({
            'page': page + 1,
            'img_id': img_id,
            'csv_index': csv_index,
            'csv_rows': csv_rows
        })
        time.sleep(random.uniform(60, 5*60))
        page+=1
        fail_count=0

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"第 {page} 页失败: {error_msg}")
        # save_state({
        #     'page': page-1,
        #     'img_id': img_id,
        #     'csv_index': csv_index,
        #     'csv_rows': csv_rows
        # })
        fail_count+=1
        print(f"第 {page} 页请求失败，正在重试... (连续失败 {fail_count} 次)")
        if fail_count>=3:
            break
        time.sleep(2500)
        continue


print(f"完成！共 {img_id-1} 张图片")
