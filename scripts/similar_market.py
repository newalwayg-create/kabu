"""今の日経平均と「チャートの形」が似ている過去の相場を探す (類似チャート検索).

直近 W 営業日の日経平均 (対数価格) を基準パターンとし、
過去の日経平均・世界の株価指数・日米の個別株について、同じ長さの全期間をスライドしながら比較する.

一致率の指標
  - 形状相関 r  : 対数価格パス同士のピアソン相関 (形そのものの一致. 値幅の大小は無視)
  - 5日リターン相関: 5営業日リターン列の相関 (トレンドだけ一致している“見かけの相似”を見分ける)
  - 一致率(%)   : 100 × (0.7·形状相関 + 0.3·5日リターン相関)  ←ランキングに使用
  - 値幅倍率     : 候補の対数価格レンジ ÷ 今回の対数価格レンジ (1 に近いほど値動きの大きさも近い)
その後 60 営業日の騰落も記録し、類似局面の「その後」を集計する (予測ではない).

    python scripts/similar_market.py            # データ取得 + 分析
    python scripts/similar_market.py --cache DIR  # DIR/idx.pkl, stk.pkl を使う
出力: output/similar_market.{md,csv}, output/similar_market_web.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "output"
QUERY = "^N225"
WINDOWS = (250, 120)  # 約1年 / 約半年
FWD = 60
W_SHAPE, W_RET = 0.7, 0.3

INDICES = {
    "^N225": "日経平均", "^GSPC": "S&P500", "^DJI": "NYダウ", "^IXIC": "NASDAQ総合",
    "^NDX": "NASDAQ100", "^SOX": "SOX指数", "^RUT": "ラッセル2000", "^HSI": "ハンセン指数",
    "^GDAXI": "独DAX", "^FTSE": "英FTSE100", "^STOXX50E": "ユーロストックス50",
    "^TWII": "台湾加権", "^KS11": "韓国KOSPI", "1306.T": "TOPIX連動ETF",
}
US = ("AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO AMD INTC CSCO ORCL QCOM TXN MU AMAT LRCX KLAC "
      "TSM ASML IBM HPQ DELL SMCI ARM NFLX ADBE CRM JPM BAC GS C WFC XOM CVX GE CAT BA MMM KO "
      "PG JNJ PFE MRK WMT HD MCD DIS NKE SBUX COST LLY UNH V MA PLTR COIN MSTR SHOP SNOW CRWD NOW").split()
JP = {
    "8035": "東京エレクトロン", "6857": "アドバンテスト", "6920": "レーザーテック", "7735": "SCREEN",
    "6146": "ディスコ", "6723": "ルネサス", "4063": "信越化学", "6501": "日立", "6758": "ソニーG",
    "6861": "キーエンス", "9984": "ソフトバンクG", "9983": "ファーストリテイリング", "7203": "トヨタ",
    "7267": "ホンダ", "6902": "デンソー", "8306": "三菱UFJ", "8316": "三井住友FG", "8411": "みずほFG",
    "8058": "三菱商事", "8031": "三井物産", "8001": "伊藤忠", "7011": "三菱重工", "7012": "川崎重工",
    "7013": "IHI", "6981": "村田製作所", "6762": "TDK", "6954": "ファナック", "6367": "ダイキン",
    "4519": "中外製薬", "4568": "第一三共", "4502": "武田薬品", "9432": "NTT", "9433": "KDDI",
    "6098": "リクルート", "7974": "任天堂", "5803": "フジクラ", "5802": "住友電工", "5801": "古河電工",
    "4062": "イビデン", "6526": "ソシオネクスト", "8766": "東京海上", "8801": "三井不動産",
    "9020": "JR東日本", "6503": "三菱電機", "6702": "富士通", "6752": "パナソニック", "7751": "キヤノン",
    "4661": "オリエンタルランド", "2914": "JT", "6273": "SMC",
}


def label(t: str) -> str:
    if t in INDICES:
        return INDICES[t]
    if t.endswith(".T") and t[:-2] in JP:
        return f"{JP[t[:-2]]}({t[:-2]})"
    return t


def kind(t: str) -> str:
    if t == QUERY:
        return "過去の日経平均"
    if t in INDICES:
        return "海外・国内指数"
    return "日本株" if t.endswith(".T") else "米国株"


def load(cache: Path | None) -> pd.DataFrame:
    if cache:
        a = pd.read_pickle(cache / "idx.pkl")
        b = pd.read_pickle(cache / "stk.pkl")
    else:
        import yfinance as yf
        dl = lambda tk: yf.download(tk, period="max", auto_adjust=True, progress=False, threads=True)["Close"]
        a = dl(list(INDICES))
        b = dl(US + [c + ".T" for c in JP])
    return pd.concat([a, b], axis=1, sort=True)


def rolling_corr(x: np.ndarray, q: np.ndarray) -> np.ndarray:
    """x の長さ len(q) の全スライド窓と q のピアソン相関."""
    w = len(q)
    qz = (q - q.mean()) / q.std()
    win = np.lib.stride_tricks.sliding_window_view(x, w)
    mu = win.mean(1, keepdims=True)
    sd = win.std(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return ((win - mu) @ qz) / (w * sd)


def search(px: pd.DataFrame, w: int) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    q_s = px[QUERY].dropna()
    q = np.log(q_s.values[-w:])
    q_dates = q_s.index[-w:]
    q_ret5 = q[5:] - q[:-5]
    q_range = q.max() - q.min()
    rows, nows = [], []
    for t in px.columns:
        s = px[t].dropna()
        s = s[s > 0]
        if len(s) < w + 10:
            continue
        lx = np.log(s.values)
        shape = rolling_corr(lx, q)
        rr = rolling_corr(lx[5:] - lx[:-5], q_ret5)
        win = np.lib.stride_tricks.sliding_window_view(lx, w)
        rng = win.max(1) - win.min(1)
        score = W_SHAPE * shape + W_RET * rr
        end_idx = np.arange(w - 1, len(lx))
        now_row = None
        if s.index[-1] >= q_dates[-1] - pd.Timedelta(days=10):  # 同時期 (直近窓) の一致度
            now_row = dict(ticker=t, name=label(t), kind=kind(t), score=float(score[-1]),
                           shape_r=float(shape[-1]), ret5_r=float(rr[-1]), amp=float(rng[-1] / q_range),
                           path=(lx[-w:] - lx[-1]).tolist())
            if t != QUERY:
                nows.append(now_row)
        # 過去の類似局面: 基準期間と1日でも重なる窓は除外 (同時期の連動と区別する)
        score[s.index[end_idx] >= q_dates[0]] = np.nan
        # 候補ごとに非重複で上位を拾う (窓の半分以内の近接は同一局面とみなす)
        order = np.argsort(-np.nan_to_num(score, nan=-9))
        taken: list[int] = []
        for i in order[:4000]:
            if np.isnan(score[i]) or score[i] < 0.5 or len(taken) >= 2:
                break
            if any(abs(i - j) < w // 2 for j in taken):
                continue
            taken.append(i)
            e = end_idx[i]
            fwd = lx[e + FWD] - lx[e] if e + FWD < len(lx) else np.nan
            fwd_path = (lx[e:e + FWD + 1] - lx[e]).tolist()
            rows.append(dict(
                ticker=t, name=label(t), kind=kind(t),
                start=s.index[e - w + 1].date(), end=s.index[e].date(),
                score=score[i], shape_r=shape[i], ret5_r=rr[i],
                amp=rng[i] / q_range,
                fwd60=np.expm1(fwd) if not np.isnan(fwd) else np.nan,
                path=(lx[e - w + 1:e + 1] - lx[e]).tolist(),
                fwd_path=fwd_path,
            ))
    df = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    qpath = pd.Series(q - q[-1], index=q_dates)
    now = pd.DataFrame(nows).sort_values("score", ascending=False).reset_index(drop=True)
    return df, qpath, now


# 有名な暴落局面: (名前, 窓の終わりを探す期間, 比較する銘柄)
EPISODES = [
    ("ITバブル崩壊", "1999-07-01", "2001-12-31", ["^IXIC", "^NDX", "^SOX", "^N225", "CSCO", "INTC"]),
    ("リーマンショック", "2007-06-01", "2009-06-30", ["^GSPC", "^DJI", "^N225", "^GDAXI", "^HSI", "^SOX"]),
    ("ブラックマンデー", "1987-08-01", "1988-03-31", ["^GSPC", "^N225"]),
    ("日本のバブル崩壊", "1989-10-01", "1990-12-31", ["^N225"]),
]


def episodes(px: pd.DataFrame, w: int) -> list[dict]:
    """各暴落局面の中で、今の形に最も近い窓を探す (窓の終わりが指定期間内のもの)."""
    q = np.log(px[QUERY].dropna().values[-w:])
    qr, q_range = q[5:] - q[:-5], q.max() - q.min()
    rows = []
    for ep, a, b, tks in EPISODES:
        for t in tks:
            s = px[t].dropna()
            s = s[s > 0]
            lx = np.log(s.values)
            shape = rolling_corr(lx, q)
            rr = rolling_corr(lx[5:] - lx[:-5], qr)
            win = np.lib.stride_tricks.sliding_window_view(lx, w)
            rng = win.max(1) - win.min(1)
            score = W_SHAPE * shape + W_RET * rr
            ends = s.index[w - 1:]
            m = (ends >= a) & (ends <= b)
            if not m.any():
                continue
            i = int(np.nanargmax(np.where(m, score, -9)))
            e = i + w - 1
            after = lambda k: float(np.expm1(lx[e + k] - lx[e])) if e + k < len(lx) else None
            rows.append(dict(
                ticker=t, name=label(t), kind=ep, start=s.index[i].date(), end=ends[i].date(),
                score=score[i], shape_r=shape[i], ret5_r=rr[i], amp=rng[i] / q_range,
                fwd60=after(FWD), fwd120=after(120), fwd250=after(250),
                dd250=float(np.expm1(lx[e:e + 251].min() - lx[e])),
                path=(lx[i:e + 1] - lx[e]).tolist(), fwd_path=(lx[e:e + FWD + 1] - lx[e]).tolist(),
            ))
    return rows


def summarize(df: pd.DataFrame, n: int = 20) -> dict:
    top = df[df["fwd60"].notna()].head(n)
    paths = [p for p in top["fwd_path"] if len(p) == FWD + 1]
    arr = np.expm1(np.array(paths))
    return dict(
        n=len(top), up_ratio=float((top["fwd60"] > 0).mean()),
        median=float(top["fwd60"].median()), mean=float(top["fwd60"].mean()),
        p25=float(top["fwd60"].quantile(.25)), p75=float(top["fwd60"].quantile(.75)),
        band_med=np.median(arr, 0).tolist(), band_lo=np.quantile(arr, .25, 0).tolist(),
        band_hi=np.quantile(arr, .75, 0).tolist(),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path)
    args = ap.parse_args()
    px = load(args.cache)
    OUT.mkdir(exist_ok=True)
    web = {"asof": str(px[QUERY].dropna().index[-1].date()),
           "last": float(px[QUERY].dropna().iloc[-1]), "windows": {}}
    md = [f"# 今の日経平均に似た相場 (類似チャート検索)\n",
          f"基準: 日経平均 終値 {web['last']:,.0f} 円 ({web['asof']})\n"]
    csvs = []
    for w in WINDOWS:
        df, qpath, now = search(px, w)
        df["window"] = w
        csvs.append(df.drop(columns=["path", "fwd_path"]))
        summ = summarize(df)
        web["windows"][str(w)] = {
            "query": {"dates": [str(d.date()) for d in qpath.index], "path": qpath.tolist(),
                      "close": px[QUERY].dropna().values[-w:].tolist()},
            "matches": [
                {k: (str(v) if k in ("start", "end") else v) for k, v in r.items()}
                for r in df.head(40).replace({np.nan: None}).to_dict("records")
            ],
            "by_kind": {
                k: [{kk: (str(vv) if kk in ("start", "end") else vv) for kk, vv in r.items()}
                    for r in g.head(10).replace({np.nan: None}).to_dict("records")]
                for k, g in df.groupby("kind")
            },
            "summary": summ,
            "now": now.head(15).to_dict("records"),
            "episodes": [{k: (str(v) if k in ("start", "end") else v) for k, v in r.items()} for r in episodes(px, w)],
        }
        md.append(f"\n## 直近 {w} 営業日 ({qpath.index[0].date()} 〜 {qpath.index[-1].date()})\n")
        md.append("### 同時期に同じ形で動いている銘柄 (連動の強さ)\n")
        md.append("| # | 銘柄 | 区分 | 一致率 | 形状相関 | 5日リターン相関 | 値幅倍率 |")
        md.append("|---|---|---|---|---|---|---|")
        for i, r in now.head(10).iterrows():
            md.append(f"| {i+1} | {r['name']} | {r.kind} | {r.score:.1%} | {r.shape_r:.3f} | {r.ret5_r:.3f} | {r.amp:.2f} |")
        md.append("\n### 過去の類似局面 (基準期間と重ならない窓のみ)\n")
        md.append(f"類似上位20局面の『その後60営業日』: 上昇 {summ['up_ratio']:.0%} / "
                  f"中央値 {summ['median']:+.1%} (25〜75%: {summ['p25']:+.1%} 〜 {summ['p75']:+.1%})\n")
        md.append("| # | 銘柄 | 区分 | 期間 | 一致率 | 形状相関 | 5日リターン相関 | 値幅倍率 | その後60日 |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for i, r in df.head(25).iterrows():
            f = "—" if pd.isna(r.fwd60) else f"{r.fwd60:+.1%}"
            md.append(f"| {i+1} | {r['name']} | {r.kind} | {r.start} 〜 {r.end} | {r.score:.1%} | "
                      f"{r.shape_r:.3f} | {r.ret5_r:.3f} | {r.amp:.2f} | {f} |")
    pd.concat(csvs).to_csv(OUT / "similar_market.csv", index=False)
    (OUT / "similar_market.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "similar_market_web.json").write_text(json.dumps(web, ensure_ascii=False), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
