#!/usr/bin/env python3
"""Render the reviewed bibliography into browsable Chinese Markdown."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "心理学学习研究"


def render():
    data = json.loads((LIBRARY / "catalog.json").read_text(encoding="utf-8"))
    books = data["items"]
    lines = ["# 心理学学习研究", "", "中文导航与研究笔记；电子书以原文版本为主。", "",
             "收录标准：流派代表人物的一手著作、大学开放教材及可核实出处的奠基论文。这里的‘经典’是书目编选判断，不代表其中每个观点仍获当代研究支持。", "",
             f"首批核对日期：{data['reviewed_on']}。共 {len(books)} 条资源，其中图书/教材 {sum(b['kind'] == 'book' for b in books)} 条、论文 {sum(b['kind'] == 'article' for b in books)} 条。", "",
             "## 从这里开始", "", "- [完整书目与获取入口](书目总览.md)", "- [12 周阅读路线](学习路线.md)",
             "- [电子书获取说明](电子书/README.md)", "- [自动检索候选](检索报告/最新候选.md)",
             "- [读书笔记模板](研究笔记/读书笔记模板.md)", "- [文献引用模板](研究笔记/文献引用模板.md)", "",
             "## 分类", "", "历史学派、当代理论取向与研究分支并不处于同一个分类层级；以下目录为学习导航，避免把所有分支都称作独立门派。", ""]
    all_rows = ["# 书目总览", "", "每条链接对应下列指定版本或档案。‘免费阅读’与‘允许转载’分别记录；目录/书商页面不等于已取得全文。中文书名为常见译名或说明性译名，并不表示已找到获授权的中文电子版。", "",
                "PDF 页码与正文原文：本目录没有摘录书中论述，未作页码定位。引用原著时请在笔记中另填所用版本、章节、PDF 页码及短引文。", ""]
    for school in data["schools"]:
        selected = [b for b in books if b["school"] == school["id"]]
        folder = LIBRARY / school["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        lines.append(f"- [{school['name']}]({school['folder']}/README.md)：{len(selected)} 条")
        detail = [f"# {school['name']}", "", f"研究问题：{school['question']}", "",
                  "按下列顺序选读；带有‘论文’标记的资源不是完整电子书。", ""]
        all_rows += [f"## {school['name']}", "", "| 中文书名 / 原文名 | 作者 | 原作年份 | 类型 | 获取情况 |", "| --- | --- | --- | --- | --- |"]
        for b in selected:
            all_rows.append(f"| [{b['title_zh']}]({school['folder']}/README.md#{b['id']}) / {b['title']} | {b['author']} | {b['original_year']} | {'图书' if b['kind'] == 'book' else '论文'} | [{b['access_label']}]({b['url']}) |")
            detail += [f"<a id=\"{b['id']}\"></a>", f"## {b['title_zh']}", "", f"- 原文：{b['title']}", f"- 作者：{b['author']}",
                       f"- 原作年份：{b['original_year']}；类型：{'图书/教材' if b['kind'] == 'book' else '经典论文'}。",
                       f"- 所链接版本：{b['edition']}", f"- 获取：[{b['access_label']}]({b['url']})", f"- 来源：{b['provider']}",
                       f"- 授权与保存：{b['rights']}", f"- 选读目的：{b['purpose']}"]
            if b.get("gutenberg_id"):
                detail += [f"- 官方 EPUB：[下载入口](https://www.gutenberg.org/ebooks/{b['gutenberg_id']}.epub3)；可用仓库脚本按编号 {b['id']} 下载。"]
            if b.get("download_url"):
                detail += [f"- 官方文件：[下载 / 阅读]({b['download_url']})"]
            detail += [f"- 书目核对：{data['reviewed_on']}。访问入口可能因地区、机构订阅或网站变更而变化。", ""]
        (folder / "README.md").write_text("\n".join(detail), encoding="utf-8")
        all_rows.append("")
    lines += ["", "## 使用规则", "", "优先使用出版社、大学档案和开放书库。自动检索只生成待核验候选，不自动把搜索命中认定为权威经典，也不把借阅、预览或版权状态不明的资源标为可自由下载。", "",
              "书目核验说明见 [来源与维护规则](来源与维护规则.md)。"]
    (LIBRARY / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (LIBRARY / "书目总览.md").write_text("\n".join(all_rows) + "\n", encoding="utf-8")
    print(json.dumps({"resources": len(books), "types": dict(Counter(b['kind'] for b in books)), "categories": len(data['schools'])}, ensure_ascii=False))


if __name__ == "__main__":
    render()

