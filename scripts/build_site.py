"""
读取 data/*.json，用 templates/index.html.jinja 渲染出最终页面到 docs/index.html
（docs/ 是 GitHub Pages 常用的发布目录，仓库设置里选 "Deploy from branch: main /docs" 即可）
"""
import json
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)


def load_json(name, default):
    path = DATA_DIR / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    global_news = load_json("news_global.json", [])
    chengdu_news = load_json("news_chengdu.json", [])
    gpu_prices = load_json("gpu_prices.json", [])

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    template = env.get_template("index.html.jinja")

    html = template.render(
        global_news=global_news,
        chengdu_news=chengdu_news,
        gpu_prices=gpu_prices,
        build_time=time.strftime("%Y-%m-%d %H:%M"),
    )

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"页面已生成: {DOCS_DIR / 'index.html'}")


if __name__ == "__main__":
    build()
