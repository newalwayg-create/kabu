"""Webページ（Artifact）用のHTMLを作る: python trading/build_page.py OUT.html [--preview PREVIEW.html]"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402


def build(out: str, preview: str | None = None) -> None:
    with tempfile.TemporaryDirectory() as d:
        j = Path(d) / "data.json"
        ledger.export(str(j))
        data = j.read_text(encoding="utf-8").replace("</", "<\\/")
    page = (HERE / "dashboard_template.html").read_text(encoding="utf-8").replace("__DATA__", data)
    Path(out).write_text(page, encoding="utf-8")
    if preview:
        Path(preview).write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">'
                                 + page + "</body></html>", encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    build(args[0], args[args.index("--preview") + 1] if "--preview" in args else None)
