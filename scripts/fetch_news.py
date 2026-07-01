"""
抓取"全球算力"与"成都算力"相关新闻，输出到 data/news_global.json 和 data/news_chengdu.json

设计原则：
- 只用免费、公开的 RSS 源，不需要任何 API Key
- 单个 RSS 源失效不应导致整个任务失败，所以每个源都单独 try/except
- 用关键词过滤，而不是依赖信源本身分类是否精准

注意：RSS 地址会随时间失效或改版。首次使用前建议本地跑一次
（python scripts/fetch_news.py）确认能正常抓到数据，如某个源失效，
删掉或替换成你信任的其他源即可，不影响其余部分。
"""
import json
import re
import time
from pathlib import Path

import feedparser

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 关键词：命中任意一个即视为"算力相关"
GLOBAL_KEYWORDS = ["算力", "AI芯片", "GPU", "数据中心", "智算", "超算", "AI infrastructure", "compute cluster"]
CHENGDU_KEYWORDS = ["成都"]  # 会与 GLOBAL_KEYWORDS 组合使用（见下方逻辑）

# 免费公开 RSS 源（无需 Key）。按需增删。
FEEDS = [
    "https://www.ithome.com/rss/",
    "https://www.36kr.com/feed",
    "https://rss.sina.com.cn/roll/finance/hot_roll.xml",
    "http://www.people.com.cn/rss/tech.xml",
    "https://www.cls.cn/nodeRss/1000",  # 财联社（如失效可替换）
]


def contains_keyword(text, keywords):
    return any(k.lower() in text.lower() for k in keywords)


def clean_html(raw):
    return re.sub("<[^<]+?>", "", raw or "").strip()


def fetch_all():
    global_items, chengdu_items = [], []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:50]:
                title = entry.get("title", "")
                summary = clean_html(entry.get("summary", ""))[:120]
                link = entry.get("link", "")
                published = entry.get("published", "") or time.strftime("%Y-%m-%d")
                full_text = f"{title} {summary}"

                item = {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published,
                    "source": feed.feed.get("title", url),
                }

                if contains_keyword(full_text, CHENGDU_KEYWORDS) and contains_keyword(full_text, GLOBAL_KEYWORDS):
                    chengdu_items.append(item)
                elif contains_keyword(full_text, GLOBAL_KEYWORDS):
                    global_items.append(item)
        except Exception as e:
            print(f"[warn] 抓取失败，跳过该源: {url} ({e})")
            continue

    # 去重（按标题）
    def dedup(items):
        seen, out = set(), []
        for it in items:
            if it["title"] not in seen:
                seen.add(it["title"])
                out.append(it)
        return out

    global_items = dedup(global_items)[:10]
    chengdu_items = dedup(chengdu_items)[:10]

    (DATA_DIR / "news_global.json").write_text(
        json.dumps(global_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "news_chengdu.json").write_text(
        json.dumps(chengdu_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"全球算力: {len(global_items)} 条 | 成都算力: {len(chengdu_items)} 条")


if __name__ == "__main__":
    fetch_all()
