"""output/similar_market_web.json から重ね合わせチャートの HTML を作る.

    python scripts/similar_market.py && python scripts/build_similar_html.py
出力: output/similar_market.html
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output" / "similar_market_web.json"
TPL = ROOT / "scripts" / "similar_market_template.html"
OUT = ROOT / "output" / "similar_market.html"

KEYS = ("name", "kind", "ticker", "start", "end", "score", "shape_r", "ret5_r", "amp", "fwd60", "fwd120", "fwd250", "dd250")


def slim(r: dict, with_fwd: bool = True) -> dict:
    o = {k: (round(r[k], 4) if isinstance(r.get(k), float) else r.get(k)) for k in KEYS if k in r}
    o["path"] = [round(x, 4) for x in r["path"]]
    if with_fwd and r.get("fwd_path"):
        o["fwd"] = [round(x, 4) for x in r["fwd_path"]]
    return o


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    out = {"asof": d["asof"], "last": d["last"], "windows": {}}
    for w, v in d["windows"].items():
        hist = v["matches"][:25]
        seen = {(m["ticker"], m["end"]) for m in hist}
        extra = []
        for k in ("過去の日経平均", "海外・国内指数"):
            for m in v["by_kind"].get(k, [])[:4]:
                if (m["ticker"], m["end"]) not in seen:
                    extra.append(m)
                    seen.add((m["ticker"], m["end"]))
        s = v["summary"]
        out["windows"][w] = {
            "dates": v["query"]["dates"],
            "close": [round(x, 1) for x in v["query"]["close"]],
            "hist": [slim(m) for m in hist + extra],
            "now": [slim(m, False) for m in v["now"][:10]],
            "episodes": [slim(m) for m in v["episodes"]],
            "summary": {k: (round(x, 4) if isinstance(x, float) else [round(y, 4) for y in x] if isinstance(x, list) else x)
                        for k, x in s.items()},
        }
    html = TPL.read_text(encoding="utf-8").replace("__DATA__", json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    OUT.write_text(html, encoding="utf-8")
    print(OUT, f"{OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
