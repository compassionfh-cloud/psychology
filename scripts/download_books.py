#!/usr/bin/env python3
"""Download explicitly selected Gutenberg EPUBs; never bypass access controls."""
import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_epub(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.read("mimetype").strip() != b"application/epub+zip":
            raise ValueError("not an EPUB")
        if "META-INF/container.xml" not in z.namelist():
            raise ValueError("EPUB container missing")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", required=True, help="catalog ID; repeat to download several books")
    parser.add_argument("--output", default=str(ROOT / ".local" / "ebooks"))
    args = parser.parse_args()
    items = json.loads((ROOT / "心理学学习研究" / "catalog.json").read_text(encoding="utf-8"))["items"]
    by_id = {b["id"]: b for b in items}
    for key in args.id:
        if key not in by_id or not by_id[key].get("gutenberg_id"):
            parser.error(f"{key}: not a reviewed Gutenberg item")
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    failed = False
    for key in dict.fromkeys(args.id):
        book = by_id[key]
        number = int(book["gutenberg_id"])
        url = f"https://www.gutenberg.org/ebooks/{number}.epub3"
        path = directory / f"{key}.epub"
        # Validate local copies too; a prior failed HTTP response must not count as a book.
        if path.exists():
            try:
                validate_epub(path.read_bytes())
                print(key, "already downloaded")
                continue
            except (ValueError, zipfile.BadZipFile, KeyError):
                pass
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PsychologyStudyLibrary/1.0"})
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read(25_000_001)
            if len(raw) > 25_000_000:
                raise ValueError("file exceeds 25 MB")
            validate_epub(raw)
            temporary = path.with_suffix(".part")
            temporary.write_bytes(raw)
            temporary.replace(path)
            manifest[key] = {"title": book["title"], "source": book["url"], "download_url": url,
                             "rights": book["rights"], "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            print(key, "OK", len(raw))
        except Exception as error:
            failed = True
            print(key, "FAILED", type(error).__name__, str(error))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

