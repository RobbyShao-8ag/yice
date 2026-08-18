#!/usr/bin/env python3
"""Import the 384 canonical line texts from Chinese Wikisource.

The script is intentionally stdlib-only and reproducible.  The public-domain
Chinese source text becomes the runtime-facing ``text``/``source_text``; the
previous unverified translation is deliberately not retained.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://zh.wikisource.org/w/api.php"
PAGE_NAMES = [
    "乾", "坤", "屯", "蒙", "需", "訟", "師", "比", "小畜", "履", "泰",
    "否", "同人", "大有", "謙", "豫", "隨", "蠱", "臨", "觀", "噬嗑",
    "賁", "剝", "復", "无妄", "大畜", "頤", "大過", "坎", "離", "咸",
    "恒", "遯", "大壯", "晉", "明夷", "家人", "睽", "蹇", "解", "損",
    "益", "夬", "姤", "萃", "升", "困", "井", "革", "鼎", "震", "艮",
    "漸", "歸妹", "豐", "旅", "巽", "兌", "渙", "節", "中孚", "小過",
    "既濟", "未濟",
]
SOURCE_TEMPLATE = "https://zh.wikisource.org/wiki/周易/{name}"


def fetch_all_wikitext(page_names: list[str]) -> dict[str, str]:
    """Fetch pages in two polite MediaWiki API batches."""
    result: dict[str, str] = {}
    for start in range(0, len(page_names), 32):
        chunk = page_names[start : start + 32]
        titles = [f"周易/{name}" for name in chunk]
        query = urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "formatversion": 2,
                "format": "json",
                "titles": "|".join(titles),
            }
        )
        request = urllib.request.Request(
            f"{API_URL}?{query}",
            headers={"User-Agent": "yice-data-importer/1.0 (open-source project)"},
        )
        payload = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        if payload is None or "error" in payload:
            raise RuntimeError(f"Wikisource batch failed: {payload}")
        for page in payload["query"]["pages"]:
            if page.get("missing"):
                raise RuntimeError(f"Wikisource page missing: {page['title']}")
            content = page["revisions"][0]["slots"]["main"]["content"]
            result[page["title"].split("/", 1)[1]] = content
        if start + 32 < len(page_names):
            time.sleep(1)
    return result


def clean_markup(value: str) -> str:
    value = re.sub(r"-\{(.*?)\}-", r"\1", value)
    value = re.sub(r"\{\{.*?\}\}", "", value)
    value = re.sub(r"''+", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def parse_six_lines(wikitext: str) -> list[tuple[str, str]]:
    matches = re.findall(
        r'^\*#<span style="color:blue">(.*?)(?:</span>)?$',
        wikitext,
        flags=re.MULTILINE,
    )
    parsed: list[tuple[str, str]] = []
    for raw in matches:
        clean = clean_markup(raw)
        parts = re.split(r"[：，,:]", clean, maxsplit=1)
        if len(parts) != 2:
            continue
        line_name, source_text = parts
        if re.fullmatch(r"(?:初[九六]|[九六][二三四五]|上[九六])", line_name):
            parsed.append((line_name, source_text))
        if len(parsed) == 6:
            break
    if len(parsed) != 6:
        raise ValueError(f"expected six line texts, got {len(parsed)}")
    return parsed


def main() -> int:
    lines_path = ROOT / "data" / "lines.json"
    hexagrams_path = ROOT / "data" / "hexagrams.json"
    lines = json.loads(lines_path.read_text(encoding="utf-8"))
    hexagrams = json.loads(hexagrams_path.read_text(encoding="utf-8"))
    by_id = {line["id"]: line for line in lines}
    source_pages = fetch_all_wikitext(PAGE_NAMES)

    from core.yao_lines import get_yao_name

    for hexagram_id, page_name in enumerate(PAGE_NAMES, 1):
        print(f"[{hexagram_id:02d}/64] 周易/{page_name}", flush=True)
        parsed = parse_six_lines(source_pages[page_name])
        binary_code = hexagrams[str(hexagram_id)]["binary_code"]
        for position, (_source_name, source_text) in enumerate(parsed, 1):
            record = by_id[f"{hexagram_id}-{position}"]
            record.update(
                {
                    "yao_name": get_yao_name(position, binary_code),
                    "source_text": source_text,
                    "text": source_text,
                    "plain_explanation": record.get("plain_explanation", ""),
                    "source": SOURCE_TEMPLATE.format(
                        name=urllib.parse.quote(page_name)
                    ),
                }
            )
            record.pop("legacy_translation", None)

    lines_path.write_text(
        json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {len(lines)} records in {lines_path}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
