"""「思惑相場の基本パターン」(急騰 → 天井 → 上げ幅の5割押し → 保ち合い or ダラダラ下げ) の検証.

イベントの定義
  - 天井: 前後60営業日で最も高い終値の日
  - 起点: 天井の前 RALLY_MAX 営業日以内の最安値. 起点→天井で +MIN_GAIN 以上上げたものを「急騰」とする
  - 位置 x = (株価 - 起点) / (天井 - 起点)   0=起点(上げ幅を全部吐き出し), 1=天井, 0.5=半値押し
  - 半値タッチ: 天井後 TOUCH_MAX 営業日以内に初めて x<=0.5 になった日
  - 半値タッチの 60 営業日後に x>=0.4 なら「緑 (保ち合い)」, x<0.25 なら「青 (ダラダラ下げ)」, その間は「中間」

    python scripts/speculative_pattern.py [--cache DIR]   # DIR/jpall.pkl を使う
出力: output/speculative_pattern.{md,csv}, output/speculative_pattern.html (テンプレートがあれば)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
LOCAL = 60          # 天井判定の前後幅
RALLY_MAX = 60      # 起点から天井までの最大日数 (約3か月)
MIN_GAIN = 0.5      # 急騰の最低上昇率
TOUCH_MAX = 120     # 天井から半値タッチまでの最大日数
AFTER = 60          # 半値タッチから何日後で緑/青を判定するか
PATH_DAYS = 250     # 描画用: 天井から何日後までの軌跡を残すか
GREEN, BLUE = 0.40, 0.25
TWEET = "2026-10-06"  # 引用された投稿の日付
WATCH = {"6981.T": "村田製作所", "6762.T": "TDK", "285A.T": "キオクシアHD", "6976.T": "太陽誘電",
         "4062.T": "イビデン", "8035.T": "東京エレクトロン", "5803.T": "フジクラ", "6857.T": "アドバンテスト"}


def find_events(s: pd.Series, name: str) -> list[dict]:
    s = s.dropna()
    s = s[s > 0]
    v = s.values
    n = len(v)
    out = []
    for t in range(RALLY_MAX, n):
        lo_w, hi_w = max(0, t - LOCAL), min(n, t + LOCAL + 1)
        if v[t] < v[lo_w:hi_w].max():
            continue
        if t + 5 >= n:  # 直近5日以内の高値は天井とみなさない
            continue
        a = t - RALLY_MAX
        i_lo = a + int(np.argmin(v[a:t]))
        L, P = v[i_lo], v[t]
        if P / L - 1 < MIN_GAIN:
            continue
        seg = v[i_lo:min(n, t + PATH_DAYS + 1)]
        if np.abs(np.diff(seg) / seg[:-1]).max() > 0.45:  # 合併等によるデータの段差を含むものは除外
            continue
        x = (v[t:min(n, t + PATH_DAYS + 1)] - L) / (P - L)
        pre = (v[i_lo:t + 1] - L) / (P - L)
        touch = next((k for k in range(1, min(len(x), TOUCH_MAX + 1)) if x[k] <= 0.5), None)
        ev = dict(ticker=s.name, name=name, start=s.index[i_lo].date(), peak=s.index[t].date(),
                  rally_days=t - i_lo, gain=P / L - 1, low=L, top=P,
                  touch_day=touch, complete=t + TOUCH_MAX + AFTER < n,
                  min60=float(x[:61].min()) if len(x) > 1 else np.nan,
                  min120=float(x[:121].min()) if len(x) > 1 else np.nan,
                  x_now=float(x[-1]) if t + PATH_DAYS >= n else np.nan,
                  path=[round(float(z), 3) for z in x], pre=[round(float(z), 3) for z in pre])
        if touch is not None:
            k = touch
            ev["touch_date"] = s.index[t + k].date()
            for h in (20, 60, 120, 250):
                j = t + k + h
                ev[f"x_t{h}"] = float((v[j] - L) / (P - L)) if j < n else np.nan
                ev[f"ret_t{h}"] = float(v[j] / v[t + k] - 1) if j < n else np.nan
            xa = ev["x_t60"]
            ev["branch"] = None if np.isnan(xa) else ("緑" if xa >= GREEN else "青" if xa < BLUE else "中間")
        out.append(ev)
    return out


def x_at(s: pd.Series, r, date: str) -> float | None:
    v = s.dropna().asof(date)
    return None if pd.isna(v) or pd.Timestamp(date) < pd.Timestamp(r.peak) else round(float((v - r.low) / (r.top - r.low)), 3)


def stats(ev: pd.DataFrame) -> dict:
    done = ev[ev["complete"]]
    t = done[done["touch_day"].notna()]
    br = t["branch"].value_counts(normalize=True)
    # 半値タッチから20日後に保てているか → その後100日の騰落
    hold = t[t["x_t20"] >= 0.45]
    broke = t[t["x_t20"] < 0.35]
    fwd = lambda g: float(((1 + g["ret_t120"]) / (1 + g["ret_t20"]) - 1).median())
    return dict(
        n=len(done), touch_rate=float(done["touch_day"].notna().mean()),
        touch_med=float(t["touch_day"].median()),
        min120_med=float(done["min120"].median()),
        retrace_med=float(1 - done["min120"].median()),
        green=float(br.get("緑", 0)), mid=float(br.get("中間", 0)), blue=float(br.get("青", 0)),
        back_to_start=float((t["x_t120"] <= 0).mean()),
        hold_n=len(hold), broke_n=len(broke),
        hold_fwd=fwd(hold), broke_fwd=fwd(broke),
        hold_up=float((((1 + hold["ret_t120"]) / (1 + hold["ret_t20"])) > 1).mean()),
        broke_up=float((((1 + broke["ret_t120"]) / (1 + broke["ret_t20"])) > 1).mean()),
        rally_med=float(done["rally_days"].median()), gain_med=float(done["gain"].median()),
        # 緑なのに後で青まで崩れた割合 (半値タッチから120日後・250日後に x<0.25)
        g2b120=float((t[t.branch == "緑"]["x_t120"] < BLUE).mean()),
        g2b250=float((t[t.branch == "緑"]["x_t250"] < BLUE).mean()),
        split=split_fwd(t),
    )


def split_fwd(t: pd.DataFrame) -> dict:
    """緑/中間/青が決まった時点 (半値タッチ+60日) から先の騰落 — 見分けた後に役立つか."""
    out = {}
    for b, g in t.groupby("branch"):
        f60 = (1 + g["ret_t120"]) / (1 + g["ret_t60"]) - 1
        f190 = (1 + g["ret_t250"]) / (1 + g["ret_t60"]) - 1
        out[b] = dict(n=int(len(g)), f60=float(f60.median()), f190=float(f190.median()),
                      up60=float((f60 > 0).mean()), up190=float((f190 > 0).mean()))
    return out


def band(paths: list[list[float]], days: int = PATH_DAYS) -> dict:
    arr = np.full((len(paths), days + 1), np.nan)
    for i, p in enumerate(paths):
        arr[i, :len(p)] = p[:days + 1]
    with np.errstate(all="ignore"):
        q = np.nanpercentile(arr, [25, 50, 75], axis=0)
    return {k: [None if np.isnan(z) else round(float(z), 3) for z in q[i]] for i, k in enumerate(("lo", "med", "hi"))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path)
    args = ap.parse_args()
    if args.cache:
        px = pd.read_pickle(args.cache / "jpall.pkl")
    else:
        raise SystemExit("--cache DIR (jpall.pkl) を指定してください")
    names = {**WATCH}
    rows = []
    for c in px.columns:
        rows += find_events(px[c].rename(c), names.get(c, c[:-2]))
    ev = pd.DataFrame(rows)
    st = stats(ev)
    done = ev[ev["complete"] & ev["touch_day"].notna()]

    # 時価総額の代わりに株価水準は使えないので、上昇率の大きさで分けた成績も出す
    by_gain = {}
    for lab, g in (("+50〜100%", done[done.gain < 1]), ("+100%以上", done[done.gain >= 1])):
        br = g["branch"].value_counts(normalize=True)
        by_gain[lab] = dict(n=len(g), green=float(br.get("緑", 0)), blue=float(br.get("青", 0)))

    # 今回 (2026年) の監視銘柄
    cur = ev[(ev["ticker"].isin(WATCH)) & (pd.to_datetime(ev["peak"]) >= "2026-01-01")]
    cur = cur.sort_values("gain", ascending=False).drop_duplicates("ticker")

    md = ["# 思惑相場の基本パターンの検証\n",
          f"対象: 日本株 {px.shape[1]} 銘柄（{px.index[0].date()}〜{px.index[-1].date()}）。"
          f"天井まで{RALLY_MAX}営業日以内に+{MIN_GAIN:.0%}以上の急騰 {st['n']} 件（その後のデータがそろうもの）。\n",
          f"- 上昇日数の中央値 {st['rally_med']:.0f} 日、上昇率の中央値 +{st['gain_med']:.0%}",
          f"- 天井から{TOUCH_MAX}日以内に半値（上げ幅の5割）まで下げた割合: **{st['touch_rate']:.0%}**（到達までの中央値 {st['touch_med']:.0f} 日）",
          f"- 天井後120日で吐き出した上げ幅の中央値: {st['retrace_med']:.0%}",
          f"- 半値タッチから{AFTER}日後: 緑（x≥{GREEN}）{st['green']:.0%} / 中間 {st['mid']:.0%} / 青（x<{BLUE}）{st['blue']:.0%}",
          f"- 半値タッチから120日後に起点以下まで戻った割合: {st['back_to_start']:.0%}",
          f"- 半値タッチ20日後に保てていた {st['hold_n']} 件 → その後100日の騰落中央値 {st['hold_fwd']:+.1%}（上昇 {st['hold_up']:.0%}）",
          f"- 半値タッチ20日後に割れていた {st['broke_n']} 件 → その後100日の騰落中央値 {st['broke_fwd']:+.1%}（上昇 {st['broke_up']:.0%}）",
          f"- 緑だったのに後で青まで崩れた割合: 120日後 {st['g2b120']:.0%} / 250日後 {st['g2b250']:.0%}",
          "- 緑/中間/青が決まった後の騰落中央値（60日 / 190日）: " + " / ".join(
              f"{k} {v['f60']:+.1%}・{v['f190']:+.1%}" for k, v in st['split'].items()) + "\n",
          "## 2026年の監視銘柄\n",
          "| 銘柄 | 起点 | 天井 | 上昇率 | 半値タッチ | 現在の位置 x |", "|---|---|---|---|---|---|"]
    for _, r in cur.iterrows():
        md.append(f"| {r['name']} | {r.start} | {r.peak} | {r.gain:+.0%} | {r.get('touch_date', '—')} | {r.path[-1]:.2f} |")
    OUT.mkdir(exist_ok=True)
    ev.drop(columns=["path", "pre"]).to_csv(OUT / "speculative_pattern.csv", index=False, encoding="utf-8-sig")
    (OUT / "speculative_pattern.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(by_gain)

    # 描画用: 半値タッチ日を揃えずに「天井からの日数」で並べた位置 x の分布
    g_paths = done[done["branch"] == "緑"]["path"].tolist()
    b_paths = done[done["branch"] == "青"]["path"].tolist()
    web = dict(
        asof=str(px.index[-1].date()), universe=int(px.shape[1]), params=dict(
            rally_max=RALLY_MAX, min_gain=MIN_GAIN, touch_max=TOUCH_MAX, after=AFTER, green=GREEN, blue=BLUE),
        stats=st, by_gain=by_gain,
        band_all=band(ev[ev["complete"]]["path"].tolist()),
        band_pre=band([p[::-1] for p in ev[ev["complete"]]["pre"].tolist()], RALLY_MAX), band_green=band(g_paths), band_blue=band(b_paths),
        tweet_date=TWEET,
        watch=[dict(ticker=r.ticker, name=r["name"], x_tweet=x_at(px[r.ticker], r, TWEET),
                    close=[round(float(z), 1) for z in px[r.ticker].dropna().loc[str(r.start):].values],
                    cdates=[str(d.date()) for d in px[r.ticker].dropna().loc[str(r.start):].index], start=str(r.start), peak=str(r.peak), gain=r.gain,
                    low=r.low, top=r.top, touch=str(r.get("touch_date")) if pd.notna(r.get("touch_day")) else None,
                    rally_days=int(r.rally_days), pre=r.pre, path=r.path,
                    dates=[str(d.date()) for d in px[r.ticker].dropna().loc[str(r.peak):].index[:len(r.path)]])
               for _, r in cur.iterrows()],
        examples=[dict(name=r["name"], peak=str(r.peak), gain=r.gain, branch=r.branch,
                       ret120=r.get("ret_t120"), x120=r.get("x_t120"))
                  for _, r in done.sort_values("gain", ascending=False).head(40).iterrows()],
    )
    js = json.dumps(web, ensure_ascii=False, separators=(",", ":"), default=lambda o: None)
    tpl = ROOT / "scripts" / "speculative_template.html"
    if tpl.exists():
        (OUT / "speculative_pattern.html").write_text(tpl.read_text(encoding="utf-8").replace("__DATA__", js), encoding="utf-8")


if __name__ == "__main__":
    main()
