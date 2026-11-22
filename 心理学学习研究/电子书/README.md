# 电子书获取

**[打开完整书目与逐项下载入口](../书目总览.md)**。

这里首先保存合法获取入口、版本信息与授权说明。当前仓库没有把“已找到链接”写成“已下载全书”。

- **Project Gutenberg**：书目页提供 EPUB、HTML 或 TXT；标明美国公版，并附本机构使用条款。其他地区及不同译本的权利状态可能不同。
- **大学档案**：如 York University 的 Classics in the History of Psychology，可在线读到许多原著与论文；可读不自动等于可重新分发。
- **开放教材**：从 OpenStax、BCcampus 或作者网站获取；采用各书所标的具体 Creative Commons 条款。
- **出版社**：标明购买、机构访问、试读或目录。试读不是整本书，目录不是电子书。

下载已精选的 Gutenberg EPUB：

```bash
python3 scripts/download_books.py --id james-briefer --id freud-dreams
```

从仓库根目录运行。文件进入 `.local/ebooks/`，来源记录在该目录的 `manifest.json`。默认不上传这些文件到公开仓库。脚本只支持明确列入精选目录的 Gutenberg 编号，不抓取第三方网盘，不处理付费墙或 DRM。

电子版以原文为主。本次尚未核实可公开分发的现代中文译本合集；中文译名只用于导航。下载站连接失败时，可从书目页改用在线阅读或其他官方格式。

