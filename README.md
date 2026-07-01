# 算力观察 · 自动更新看板

每天自动抓取「全球算力热点」「成都算力热点」「10款主流显卡价格」，生成一个静态网页，
通过 GitHub Actions 定时运行 + GitHub Pages 免费托管，全程零成本。

## 5 分钟部署步骤

1. **新建仓库**：在 GitHub 上新建一个仓库（比如 `compute-watch`），把这个文件夹里的所有内容
   上传上去（可以直接拖拽到网页版 GitHub，也可以用 `git push`）。

2. **开启 GitHub Pages**：仓库 → Settings → Pages → Build and deployment →
   Source 选 `Deploy from a branch`，Branch 选 `main` / `docs`，保存。
   几分钟后就能在 `https://你的用户名.github.io/仓库名/` 看到页面。

3. **手动触发一次，检查数据**：仓库 → Actions → 选择 "每日更新算力观察看板" →
   Run workflow，手动跑一次，确认没有报错、`docs/index.html` 被正常更新提交。

4. 之后它会**每天北京时间早上 8:30 自动运行**（可以在 `.github/workflows/update.yml`
   里改 cron 时间）。

## ⚠️ 部署前必须知道的两件事

**1. 新闻抓取（免费方案）覆盖面有限。**
用的是公开 RSS 源（IT之家、36氪、新浪财经滚动、人民网科技等），按"算力/AI芯片/GPU/
数据中心"等关键词过滤。这意味着：
- 不是所有算力新闻都能覆盖，尤其是"成都算力"这种细分主题，命中率会明显偏低；
- 想提高覆盖面，可以在 `scripts/fetch_news.py` 的 `FEEDS` 列表里继续加你信任的 RSS 源，
  或者换成付费新闻 API（结构完全兼容，改 `fetch_all()` 里的抓取逻辑即可，输出格式不用变）。

**2. 显卡价格抓取需要你自己核实一次，这部分我没法帮你完全测通。**
原因很直接：京东/淘宝这类电商平台反爬虫严格，直接爬商品页在技术上不稳定，
在合规上也有风险；它们的官方开放接口（如京东联盟）需要单独申请资质，不是零门槛方案。

所以 `scripts/fetch_gpu_prices.py` 默认改成从**中关村在线（ZOL）产品报价库**抓取——
它是公开的比价页面。但因为我这边的沙盒环境没有联网权限，**没办法帮你实测页面结构和
CSS 选择器是否准确**，脚本里的选择器（`.price-now`、`.mall-name` 等）目前是占位符。

**你需要做的**：
1. 打开 zol.com.cn，搜索这10款显卡型号，把 `GPU_LIST` 里的 `PLACEHOLDER_xxx.shtml`
   换成真实产品页 URL；
2. 本地跑一次 `python scripts/fetch_gpu_prices.py`，打开 `data/gpu_prices.json` 核对
   抓到的价格对不对；
3. 如果选择器不对（抓到 `null`），打开对应产品页，用浏览器"检查元素"找到价格所在的
   CSS class，替换掉 `parse_zol_page()` 里的选择器。

在你核实通过之前，网页会正常显示，只是显卡价格那一栏会显示"暂无数据"——不会导致
整个网站崩掉，这是刻意设计的兜底逻辑。

## 文件结构

```
compute-watch/
├── .github/workflows/update.yml   # 每天定时任务
├── scripts/
│   ├── fetch_news.py              # 抓算力新闻（RSS，免费）
│   ├── fetch_gpu_prices.py        # 抓显卡价格（需你核实选择器）
│   └── build_site.py              # 把 data/*.json 渲染成 docs/index.html
├── templates/index.html.jinja     # 网页模板/样式
├── data/                          # 抓取结果（JSON），每天自动更新
├── docs/index.html                # 最终网页，GitHub Pages 从这里发布
└── requirements.txt
```

## 后续可以升级的方向

- 新闻来源换成付费聚合 API（天行数据 / 聚合数据），覆盖面会好很多，一个月几十块钱；
- 显卡价格换成京东联盟官方 API（需要申请，审核通过后数据稳定性会好很多）；
- 想要非成都本地新闻也能覆盖到，可以加入"川观新闻""红星新闻"等四川本地媒体的 RSS
  （需要你自己找到对应地址）。
