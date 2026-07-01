"""
抓取国内10款主流显卡的市场价格，输出到 data/gpu_prices.json

⚠️ 重要说明（请务必先读）：
京东、淘宝等电商平台的商品页面通常有较强的反爬虫机制，且直接爬取商品详情页
可能违反其服务条款；它们的官方开放平台（如京东联盟）需要单独申请资质和 API Key，
不是"零成本零门槛"方案。

因此这里默认改用"中关村在线（ZOL）产品报价库"作为数据源 —— 它是公开可访问的
比价页面，聚合了多家电商的价格，抓取限制相对宽松，更适合零成本方案。

但是：
1. 本沙盒环境无法联网，所以下面的选择器（CSS selector）没有经过实测验证。
2. 网页结构可能会随时间改版。
第一次使用前，请务必本地跑一次 `python scripts/fetch_gpu_prices.py`，
打开生成的 data/gpu_prices.json 核对价格和链接是否正确；如果 ZOL 页面结构变了，
只需调整 parse_zol_page() 里的选择器，其余部分不用动。

如果你后续申请到了京东联盟 API Key，把 fetch_from_zol() 换成调用官方 API 即可，
其余脚本、GitHub Actions、网页渲染逻辑完全不用改。
"""
import json
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

# 10款主流显卡，及其在 ZOL 产品库中的产品页 URL。
# ⚠️ 这里的 URL 需要你自己去 zol.com.cn 搜索对应型号后替换成真实产品页地址，
# 我这边无法联网核实，先用型号名占位。
GPU_LIST = [
    {"name": "NVIDIA RTX 5090", "url": "https://detail.zol.com.cn/PLACEHOLDER_5090.shtml"},
    {"name": "NVIDIA RTX 5080", "url": "https://detail.zol.com.cn/PLACEHOLDER_5080.shtml"},
    {"name": "NVIDIA RTX 4090", "url": "https://detail.zol.com.cn/PLACEHOLDER_4090.shtml"},
    {"name": "NVIDIA RTX 4080 SUPER", "url": "https://detail.zol.com.cn/PLACEHOLDER_4080s.shtml"},
    {"name": "NVIDIA RTX 4070 Ti SUPER", "url": "https://detail.zol.com.cn/PLACEHOLDER_4070tis.shtml"},
    {"name": "NVIDIA RTX 4060 Ti", "url": "https://detail.zol.com.cn/PLACEHOLDER_4060ti.shtml"},
    {"name": "AMD RX 7900 XTX", "url": "https://detail.zol.com.cn/PLACEHOLDER_7900xtx.shtml"},
    {"name": "AMD RX 7800 XT", "url": "https://detail.zol.com.cn/PLACEHOLDER_7800xt.shtml"},
    {"name": "华为 昇腾 910B（企业级）", "url": "https://detail.zol.com.cn/PLACEHOLDER_910b.shtml"},
    {"name": "摩尔线程 MTT S80", "url": "https://detail.zol.com.cn/PLACEHOLDER_s80.shtml"},
]

# 如果抓取失败（网络问题/被反爬/URL失效），用这份兜底数据，保证网页不会崩掉，
# 只是价格会标注"数据未更新"。首次部署时也会先用到这份数据。
FALLBACK_SEED = [
    {"name": g["name"], "price": None, "unit": "CNY", "shop": "-", "updated": "从未成功抓取"}
    for g in GPU_LIST
]


def parse_zol_page(html):
    """解析 ZOL 产品页，提取京东参考价。需要你根据实际页面结构调整选择器。"""
    soup = BeautifulSoup(html, "html.parser")
    price_tag = soup.select_one(".price-now") or soup.select_one(".pro-price")  # 占位选择器，需核实
    shop_tag = soup.select_one(".mall-name")  # 占位选择器，需核实
    price = None
    if price_tag:
        digits = "".join(c for c in price_tag.get_text() if c.isdigit() or c == ".")
        price = float(digits) if digits else None
    shop = shop_tag.get_text(strip=True) if shop_tag else "京东"
    return price, shop


def fetch_from_zol():
    results = []
    for gpu in GPU_LIST:
        try:
            resp = requests.get(gpu["url"], headers=HEADERS, timeout=10)
            resp.raise_for_status()
            price, shop = parse_zol_page(resp.text)
            results.append(
                {
                    "name": gpu["name"],
                    "price": price,
                    "unit": "CNY",
                    "shop": shop,
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
