# artifact_crawl

文物数据爬虫工具集，从多家博物馆官网爬取藏品信息（名称、年代、类别、图片链接等），输出为结构化 CSV 文件。

## 爬虫列表

| 爬虫 | 数据源 | 说明 |
|------|--------|------|
| `sh` | 上海博物馆 | API 分页爬取，约 3000 页 |
| `nmc` | 中国国家博物馆 | JSONP 接口解析，约 400 页 |
| `ln` | 辽宁省博物馆 | API 分页爬取，约 2111 页 |
| `hn` | 河南博物院 | HTML 解析（BeautifulSoup），约 1114 页 |
| `gugong` | 故宫博物院 | API 分页爬取，约 9301 页 |
| `cq3x` | 重庆中国三峡博物馆 | 带 HMAC 签名的 API，约 5244 页 |
| `bili_op` | B站（京剧视频） | 搜索 250 部经典京剧剧目，输出 JSONL |

## 用法

```bash
# 安装依赖
uv sync   # 或 pip install -r pyproject.toml

# 运行单个爬虫（后台）
./run_crawl.sh hn
./run_crawl.sh ln
./run_crawl.sh gugong

# 直接运行
python crawlers/hn.py
python crawlers/cq3x.py
```

所有爬虫均支持**断点续爬**（通过 `state.json` 保存进度），输出文件位于 `output/` 目录下。

## 下载器

- `downloaders/bili_op.py` — 使用 `yt-dlp` 从 B站 批量下载京剧视频，支持断点续传和重试

## 依赖

- Python >= 3.12
- requests, beautifulsoup4, pandas, yt-dlp
