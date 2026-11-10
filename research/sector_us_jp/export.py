"""米国業種と東証33業種の結果からWebページを作る: python research/sector_us_jp/export.py OUT.html"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
data = json.load(open(ROOT / "data" / "research" / "sector_us_jp" / "results.json", encoding="utf-8"))
html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*DATA*/", json.dumps(data, ensure_ascii=False))
Path(sys.argv[1]).write_text(html, encoding="utf-8")
print("wrote", sys.argv[1], len(html))
