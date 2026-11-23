"""バブル(天井)の後、資金はどこへ向かったか — 天井後のセクター・ローテーション比較.

日経平均 (米国は S&P500) の天井日を 0 日目として、業種バスケット (等ウェイト) の
指数に対する相対パフォーマンスを並べる.
  - 過去の天井: ITバブル (2000年), リーマン前 (2007年)
  - 今回     : 2026年の天井
今回の天井からの経過日数と同じ日数で過去のローテーションを切り出し、
業種の順位の一致度 (スピアマン順位相関) を「ローテーション一致率」として出す.

    python scripts/rotation_after_peak.py [--cache DIR]   # DIR/sect.pkl を使う
出力: output/rotation_after_peak.{md,csv}, output/rotation_web.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "output"
HORIZONS = (125, 250, 500, 750)
PRE = 250
GLITCH = 0.44  # 1日で±44%超の変化はデータ不整合とみなす (2002〜05年の合併時など)

JP_BASKETS = {
    "電力": "9501 9502 9503 9504 9505 9506 9507 9509",
    "ガス": "9531 9532",
    "鉄道": "9020 9021 9022 9005 9001 9007 9008 9009",
    "通信": "9432 9433",
    "食品・飲料": "2914 2802 2502 2503 2269 2801",
    "医薬品": "4502 4568 4519 4503 4523",
    "小売(生活必需)": "8267 3382 3088 9843 7516",
    "銀行": "8306 8316 8411 8331 8354",
    "保険": "8766 8725 8630 8750",
    "不動産": "8801 8802 8830",
    "建設": "1801 1802 1803 1812 1925 1928",
    "商社": "8058 8031 8001 8053 8002",
    "海運": "9101 9104 9107",
    "資源・石油": "1605 5020 5019",
    "素材(化学・鉄鋼)": "4063 4005 4188 3407 5401",
    "自動車": "7203 7267 6902 7269 7270",
    "重工・防衛": "7011 7012 7013",
    "電子部品": "6981 6762 6971 6963",
    "半導体": "8035 6857 6920 7735 6146 6723 4062",
    "IT・ネット": "9984 4689 4704 4324 6758",
    "レジャー・ゲーム": "4661 7974 9697 9766",
    "百貨店・インバウンド": "3099 8233 7532",
}
US_ETF = {
    "公益(XLU)": "XLU", "生活必需品(XLP)": "XLP", "ヘルスケア(XLV)": "XLV", "エネルギー(XLE)": "XLE",
    "金融(XLF)": "XLF", "資本財(XLI)": "XLI", "素材(XLB)": "XLB", "一般消費財(XLY)": "XLY",
    "テクノロジー(XLK)": "XLK",
}
LEADERS = {"日本": {"半導体", "電子部品", "IT・ネット", "通信"}, "米国": {"テクノロジー(XLK)"}}  # バブルの主役
DEFENSIVE = {"電力", "ガス", "鉄道", "通信", "食品・飲料", "医薬品", "小売(生活必需)",
             "公益(XLU)", "生活必需品(XLP)", "ヘルスケア(XLV)"}
EVENTS = {  # 名前: (天井を探す期間)
    "ITバブル(2000)": ("1999-06-01", "2000-12-31"),
    "リーマン前(2007)": ("2007-01-01", "2007-12-31"),
    "今回(2026)": ("2026-01-01", "2026-12-31"),
}


def basket_index(px: pd.DataFrame, codes: list[str], peak: pd.Timestamp) -> tuple[pd.Series, int] | None:
    """天井日に価格がある銘柄だけの等ウェイト指数 (日次リターンの平均を累積)."""
    tk = [c for c in codes if c in px and pd.notna(px[c].asof(peak)) and px[c].loc[:peak].notna().sum() > 20]
    if not tk:
        return None
    r = px[tk].ffill().pct_change(fill_method=None)
    r = r.mask(r.abs() > GLITCH, 0.0)  # 合併・株式移転時のデータの段差を除去
    first = max(px[c].first_valid_index() for c in tk)  # 全銘柄のデータがそろう日 (それ以前は描かない)
    idx = (1 + r.mean(axis=1).fillna(0)).cumprod()
    return idx.where(idx.index >= first), len(tk)


def event_frame(px: pd.DataFrame, bench: str, baskets: dict[str, list[str]], a: str, b: str, ew_base: bool):
    """天井日を 0 とした相対パフォーマンス (0日目=0%) を業種ごとに返す.
    ew_base=True なら全業種の構成銘柄の等ウェイト平均 (市場平均) に対する相対値."""
    ix = px[bench].dropna()
    peak = ix.loc[a:b].idxmax()
    i0 = ix.index.get_loc(peak)
    idx = ix.index[max(0, i0 - PRE):i0 + max(HORIZONS) + 1]
    if ew_base:
        allc = sorted({c for v in baskets.values() for c in v})
        bs = basket_index(px, allc, peak)[0].reindex(ix.index)
    else:
        bs = ix
    out, counts = {}, {}
    for name, codes in baskets.items():
        res = basket_index(px, codes, peak)
        if res is None:
            continue
        bi, n = res
        rel = (bi.reindex(idx).ffill() / bs.reindex(idx)) / (bi.asof(peak) / bs.loc[peak]) - 1
        out[name] = rel.values
        counts[name] = n
    days = np.arange(len(idx)) - min(i0, PRE)
    df = pd.DataFrame(out, index=days)
    bench_path = ix.reindex(idx).values / ix.loc[peak] - 1
    return peak, df, counts, pd.Series(bench_path, index=days), idx


def spearman(a: pd.Series, b: pd.Series) -> float:
    k = a.dropna().index.intersection(b.dropna().index)
    return float(a[k].rank().corr(b[k].rank()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path)
    args = ap.parse_args()
    jp = {k: [c + ".T" for c in v.split()] for k, v in JP_BASKETS.items()}
    us = {k: [v] for k, v in US_ETF.items()}
    if args.cache:
        px = pd.read_pickle(args.cache / "sect.pkl")
    else:
        import yfinance as yf
        tk = sorted({t for v in jp.values() for t in v}) + list(US_ETF.values()) + ["^N225", "^GSPC"]
        px = yf.download(tk, period="max", auto_adjust=True, progress=False, threads=True)["Close"]

    web = {"markets": {}}
    md = ["# バブル(天井)の後、資金はどこへ向かったか\n"]
    rows = []
    for mkt, bench, baskets, bname, ew in (("日本", "^N225", jp, "日経平均", True), ("米国", "^GSPC", us, "S&P500", False)):
        evs = {}
        for ev, (a, b) in EVENTS.items():
            evs[ev] = event_frame(px, bench, baskets, a, b, ew)
        now_peak, now_df, *_ = evs["今回(2026)"]
        D = int(now_df.index.max())  # 今回の天井からの経過営業日
        base = "全22業種の等ウェイト平均" if ew else bname
        md.append(f"\n## {mkt}（天井は{bname}で判定。相対リターンの基準: {base}）\n")
        md.append("天井日: " + " / ".join(f"{ev} {v[0].date()}" for ev, v in evs.items())
                  + f"。今回は天井から {D} 営業日経過。\n")
        cur = now_df.loc[D]
        sims, sims_ex, lag = {}, {}, {}
        keep = [n for n in cur.index if n not in LEADERS[mkt]]
        for ev in ("ITバブル(2000)", "リーマン前(2007)"):
            f = evs[ev][1]
            sims[ev] = spearman(cur, f.loc[D])
            sims_ex[ev] = spearman(cur[keep], f.loc[D][keep])
            # 過去の天井後の何日目の業種順位が、今の順位に最も似ているか
            lag[ev] = [[int(d), round(spearman(cur, f.loc[d]), 3)] for d in range(10, min(751, f.index.max() + 1), 5)]
        md.append("ローテーション一致率（天井から同じ日数での業種の相対リターン順位の相関）: "
                  + " / ".join(f"{k} {v:+.2f}（主役業種を除くと {sims_ex[k]:+.2f}）" for k, v in sims.items()) + "\n")
        for ev, l in lag.items():
            best = max(l, key=lambda x: x[1])
            md.append(f"- {ev}: 今の業種順位に最も近いのは天井から {best[0]} 営業日目（一致率 {best[1]:+.2f}）\n")
        hdr = ["業種", f"今回 {D}日"] + [f"{ev[:-6]} {h}日" for ev in ("ITバブル(2000)", "リーマン前(2007)")
                                          for h in (D,) + HORIZONS]
        md.append("| " + " | ".join(hdr) + " |")
        md.append("|" + "---|" * len(hdr))
        names = list(evs["ITバブル(2000)"][1].columns)
        order = sorted(names, key=lambda n: -evs["ITバブル(2000)"][1][n].get(750, np.nan)
                       if not np.isnan(evs["ITバブル(2000)"][1][n].get(750, np.nan)) else 9)
        for n in order:
            cells = [n, f"{cur.get(n, np.nan):+.1%}"]
            row = {"市場": mkt, "業種": n, "今回": cur.get(n, np.nan)}
            for ev in ("ITバブル(2000)", "リーマン前(2007)"):
                f = evs[ev][1]
                for h in (D,) + HORIZONS:
                    v = f[n].get(h, np.nan) if n in f else np.nan
                    cells.append("—" if pd.isna(v) else f"{v:+.1%}")
                    row[f"{ev} {h}日"] = v
            rows.append(row)
            md.append("| " + " | ".join(cells) + " |")
        web["markets"][mkt] = {
            "bench": bname, "base": base, "D": D, "sims": sims, "sims_ex": sims_ex, "lag": lag,
            "leaders": sorted(LEADERS[mkt]), "asof": str(px[bench].dropna().index[-1].date()), "defensive": sorted(DEFENSIVE),
            "events": {
                ev: {"peak": str(v[0].date()), "days": v[1].index.tolist(),
                     "bench": [round(x, 4) for x in v[3].values],
                     "counts": v[2],
                     "rel": {n: [None if pd.isna(x) else round(float(x), 4) for x in v[1][n].values] for n in v[1]}}
                for ev, v in evs.items()
            },
        }
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "rotation_after_peak.csv", index=False, encoding="utf-8-sig")
    (OUT / "rotation_after_peak.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    js = json.dumps(web, ensure_ascii=False, separators=(",", ":"))
    (OUT / "rotation_web.json").write_text(js, encoding="utf-8")
    tpl = Path(__file__).with_name("rotation_template.html")
    if tpl.exists():
        (OUT / "rotation_after_peak.html").write_text(tpl.read_text(encoding="utf-8").replace("__DATA__", js), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
