"""results.json をページに埋め込む: python research/frontier/export.py OUT.html [PREVIEW.html]"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
data = (ROOT / "data/research/frontier/results.json").read_text(encoding="utf-8").replace("</", "<\\/")
page = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", data)
Path(sys.argv[1]).write_text(page, encoding="utf-8")
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' + page + "</body></html>", encoding="utf-8")
print("ok")
