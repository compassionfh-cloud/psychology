#!/usr/bin/env python3
"""Bounded, key-free discovery of book metadata. Never downloads book bodies."""
import argparse
import datetime as dt
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "心理学学习研究"
USER_AGENT = "PsychologyStudyLibrary/1.0 (educational bibliography; metadata only)"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise ValueError("metadata response exceeded 5 MB")
    return json.loads(raw)


def normalize_work_key(key):
    key = str(key)
    if re.fullmatch(r"OL\d+W", key):
        return "/works/" + key
    if re.fullmatch(r"/works/OL\d+W", key):
        return key
    raise ValueError("Unexpected Open Library work key")


def candidates(provider, result, query):
    if provider == "gutendex":
        for book in result.get("results", []):
            number = int(book["id"])
            yield {"id": f"gutenberg:{number}", "provider": "Project Gutenberg / Gutendex metadata",
                   "title": book["title"], "authors": [a["name"] for a in book.get("authors", [])],
                   "languages": book.get("languages", []), "url": f"https://www.gutenberg.org/ebooks/{number}",
                   "access_metadata": {"copyright": book.get("copyright")}, "query": query,
                   "review_status": "待核验：经典地位、版本和所在地授权尚未审核"}
    else:
        for book in result.get("docs", []):
            key = normalize_work_key(book["key"])
            yield {"id": f"openlibrary:{key}", "provider": "Open Library metadata",
                   "title": book["title"], "authors": book.get("author_name", []),
                   "first_publish_year": book.get("first_publish_year"),
                   "languages": book.get("language", []), "url": "https://openlibrary.org" + key,
                   "access_metadata": {"ebook_access": book.get("ebook_access", "unknown")}, "query": query,
                   "review_status": "待核验：书目或借阅状态不构成转载授权"}


def safe_text(value):
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def write_report(directory, payload):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "candidates.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 自动检索候选", "", f"最近运行：{payload['checked_at']}。新候选 {payload['new_count']} 条；累计保留 {len(payload['items'])} 条。", "",
             "搜索命中仅供人工筛选，可能包含重版、传记、同名作者或非经典作品。免费/借阅标记不能用来判断转载权限。失败查询不会删除已有候选。", "",
             "## 本次来源状态", "", "| 来源 / 查询 | 结果 |", "| --- | --- |"]
    for status in payload["queries"]:
        lines.append(f"| {safe_text(status['provider'])} / {safe_text(status['query'])} | {safe_text(status['status'])} |")
    lines += ["", "## 待核验书目", "", "| 书目 | 作者 | 来源 | 审核状态 |", "| --- | --- | --- | --- |"]
    for b in payload["items"]:
        lines.append(f"| [{safe_text(b['title'])}]({b['url']}) | {safe_text('; '.join(b['authors']))} | {safe_text(b['provider'])} | {safe_text(b['review_status'])} |")
    (directory / "最新候选.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args):
    config = json.loads((ROOT / "search-config.json").read_text(encoding="utf-8"))
    output = Path(args.output) if args.output else LIBRARY / "检索报告"
    previous_path = output / "candidates.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {"items": []}
    merged = {b["id"]: b for b in previous["items"]}
    old_ids = set(merged)
    statuses = []
    queries = config["queries"][:args.max_queries] if args.max_queries else config["queries"]
    for query in queries:
        provider = query["provider"]
        if provider == "gutendex":
            url = "https://gutendex.com/books/?" + urllib.parse.urlencode({"search": query["search"]})
        elif provider == "openlibrary":
            url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode({"author": query["search"], "limit": 8, "fields": "key,title,author_name,first_publish_year,language,ebook_access", "lang": "zh"})
        else:
            raise ValueError(f"Unsupported metadata provider: {provider}")
        try:
            result = fetch_json(url)
            found = list(candidates(provider, result, query["search"]))[:32]
            for b in found:
                if b["id"] in merged:
                    b["first_seen"] = merged[b["id"]].get("first_seen", "unknown")
                else:
                    b["first_seen"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
                merged[b["id"]] = b
            statuses.append({"provider": provider, "query": query["search"], "status": f"成功，返回 {len(found)} 条"})
            print(provider, query["search"], "OK", len(found), flush=True)
        except Exception as error:
            statuses.append({"provider": provider, "query": query["search"], "status": f"失败：{type(error).__name__}: {error}"})
            print(provider, query["search"], "FAILED", str(error), flush=True)
        time.sleep(1)
    payload = {"checked_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
               "new_count": len(set(merged) - old_ids), "queries": statuses,
               "items": sorted(merged.values(), key=lambda b: b["id"])}
    write_report(output, payload)
    return 0 if any(s["status"].startswith("成功") for s in statuses) else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-queries", type=int, default=0, help="0 = all configured queries")
    parser.add_argument("--output", help="optional report directory")
    args = parser.parse_args()
    if args.max_queries < 0:
        parser.error("--max-queries must be non-negative")
    raise SystemExit(run(args))

