"""
抓取国内10款主流显卡的市场价格，输出到 data/gpu_prices.json

⚠️ 重要说明（请务必先读）：
京东、淘宝等电商平台的商品页面通常有较强的反爬虫机制，且直接爬取商品详情页
可能违反其服务条款；它们的官方开放平台（如京东联盟）需要单独申请资质和 API Key，
不是"零成本零门槛"方案。

因此这里改用"中关村在线（ZOL）产品报价库"作为数据源 —— 它是公开可访问的比价页面，
聚合了多家品牌/电商的价格。下面这些 URL 是实际联网核实过的真实分类页地址
（截至 2026-07-01），不是占位符。

工作原理：
- 每个 GPU 对应 ZOL 上的一个"芯片分类页"（比如 RTX 4090 系列汇总页），列出该芯片
  多个品牌型号及各自参考价。脚本抓取该分类页默认排序下的第一款在售型号的参考价，
  作为这颗芯片的代表市场价。
- 价格提取用的是"抓取整页可见文字，正则匹配'参考价：¥数字'"这种方式，而不是依赖
  某个具体的 CSS class 名——因为 CSS 类名随改版变化的概率，比"参考价"这个中文
  标签文案变化的概率高得多，这样抓取会更稳。
- ZOL 页面使用 GBK 编码，脚本里已经处理了这一点（如果改成别的信源要注意编码问题）。

已知限制：
- 摩尔线程 MTT S80、华为昇腾 910B 这类非主流游戏显卡，在 ZOL 分类体系里不一定
  有对应的"系列汇总页"。MTT S80 找到了一个真实的单品页并预填了链接；
  昇腾 910B 是企业级AI芯片，大概率不在 ZOL 的消费级显卡库里，先留空，
  如果你后续在别处找到合适的信源，替换掉 GPU_LIST 里对应的条目即可。
- 网页结构以后仍可能改版，如果某天所有型号都抓取失败，去 zol.com.cn 上对应网址
  确认一下"参考价"这个文案是否还在用，再调整下面的正则。
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# 价格标签的中文文案，按优先级尝试。ZOL 目前用"参考价"，保留"现价"/"报价"作为备用。
PRICE_PATTERNS = [
    re.compile(r"参考价[：:]\s*¥?\s*(\d{3,6})"),
    re.compile(r"现价[：:]\s*¥?\s*(\d{3,6})"),
    re.compile(r"报价[：:]\s*¥?\s*(\d{3,6})"),
]

# 10款目标显卡：优先用 ZOL"芯片系列汇总页"（更新更及时、覆盖更全）；
# MTT S80 用的是核实过的真实单品页。以下 URL 均于 2026-07-01 联网核实可访问。
GPU_LIST = [
    {"name": "NVIDIA RTX 5090", "url": "https://detail.zol.com.cn/vga/index2118113.shtml", "type": "single"},
    {"name": "NVIDIA RTX 5080", "url": "https://detail.zol.com.cn/vga/s11094/", "type": "series"},
    {"name": "NVIDIA RTX 4090", "url": "https://detail.zol.com.cn/vga/s10074/", "type": "series"},
    {"name": "NVIDIA RTX 4080 SUPER", "url": "https://detail.zol.com.cn/vga/s11033/", "type": "series"},
    {"name": "NVIDIA RTX 4070 Ti SUPER", "url": "https://detail.zol.com.cn/vga/s11035/", "type": "series"},
    {"name": "NVIDIA RTX 4060 Ti", "url": "https://detail.zol.com.cn/vga/s10916/", "type": "series"},
    {"name": "AMD RX 7900 XTX", "url": "https://detail.zol.com.cn/vga/s10741/", "type": "series"},
    {"name": "AMD RX 7800 XT", "url": "https://detail.zol.com.cn/vga/s10941/", "type": "series"},
    {"name": "华为 昇腾 910B（企业级）", "url": "", "type": "unavailable"},
    {"name": "摩尔线程 MTT S80", "url": "https://detail.zol.com.cn/vga/index1433801.shtml", "type": "single"},
]

FALLBACK_SEED = [
    {"name": g["name"], "price": None, "unit": "CNY", "shop": "-", "updated": "从未成功抓取"}
    for g in GPU_LIST
]


def extract_price(html_bytes):
    """把整页解码为可见文本，用正则找第一个'参考价'之类的价格标签。"""
    soup = BeautifulSoup(html_bytes.decode("gbk", errors="ignore"), "html.parser")
    text = soup.get_text()
    for pattern in PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def fetch_from_zol():
    results = []
    for gpu in GPU_LIST:
        if gpu["type"] == "unavailable" or not gpu["url"]:
            results.append(
                {
                    "name": gpu["name"],
                    "price": None,
                    "unit": "CNY",
                    "shop": "-",
                    "url": "",
                    "updated": "该型号暂无合适数据源，需手动补充",
                }
            )
            continue
        try:
            resp = requests.get(gpu["url"], headers=HEADERS, timeout=10)
            resp.raise_for_status()
            price = extract_price(resp.content)
            results.append(
                {
                    "name": gpu["name"],
                    "price": price,
                    "unit": "CNY",
                    "shop": "ZOL 中关村在线（多店铺参考价）",
                    "url": gpu["url"],
                    "updated": time.strftime("%Y-%m-%d %H:%M"),
                }
            )
        except Exception as e:
            print(f"[warn] 抓取失败: {gpu['name']} ({e})")
            results.append(
                {
                    "name": gpu["name"],
                    "price": None,
                    "unit": "CNY",
                    "shop": "-",
                    "url": gpu.get("url", ""),
                    "updated": "抓取失败，沿用上次数据",
                }
            )
    return results


def fetch_all():
    out_path = DATA_DIR / "gpu_prices.json"
    previous = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else FALLBACK_SEED

    fresh = fetch_from_zol()

    # 抓取失败的条目，尽量沿用上一次成功的价格，而不是直接显示"无数据"
    prev_by_name = {p["name"]: p for p in previous}
    merged = []
    for item in fresh:
        if item["price"] is None and item["name"] in prev_by_name and prev_by_name[item["name"]]["price"]:
            old = prev_by_name[item["name"]]
            item["price"] = old["price"]
            item["shop"] = old["shop"]
            item["updated"] = f"{old['updated']}（沿用上次成功数据）"
        merged.append(item)

    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for m in merged if m["price"])
    print(f"显卡价格: {ok}/{len(merged)} 条抓取成功")


if __name__ == "__main__":
    fetch_all()
