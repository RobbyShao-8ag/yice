# 数据来源

## 《周易》卦爻辞

- 来源：[维基文库《周易》](https://zh.wikisource.org/wiki/周易)
- 页面范围：`周易/乾` 至 `周易/未濟`，每条记录的 `source` 字段保存具体页面。
- 原作状态：公有领域；维基文库页面内容按 CC BY-SA 4.0 提供。
- 导入方式：`python scripts/import_wikisource_lines.py`

`source_text` 与 `text` 保存经典中文原文；旧的英文 Wilhelm 数据未继续
保留，因为其来源与许可链没有在仓库内得到充分证明。`yao_name` 由卦象的
`binary_code` 和爻位计算，避免人工维护造成阴阳爻名不一致。
