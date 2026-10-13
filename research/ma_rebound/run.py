"""検証の実行と結果表の出力 → results/*.md, data/*.csv"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis import HORIZONS, PNAME, build, index_features, load_prices, reliability, summarize, D
from universe import UNIVERSE

R = Path(__file__).resolve().parent / "results"
R.mkdir(exist_ok=True)
GROUP_ORDER = [f"{PNAME[p]}｜{s}" for p in range(1, 8) for s in ("上向き", "下向き")] + \
              [f"{PNAME[0]}｜上向き", f"{PNAME[0]}｜下向き"]


def md(df: pd.DataFrame, floatfmt=".2f") -> str:
    return df.to_markdown(floatfmt=floatfmt)


def run_setting(prices, idx, s, m, l, k, tag, title) -> pd.DataFrame:
    base = build(prices, idx, s, m, l, k)
    RD = R / tag
    RD.mkdir(exist_ok=True)
    DD = D / tag
    DD.mkdir(exist_ok=True)
    out = [f"# {title}（短期{s}・中期{m}・長期{l}日の単純移動平均、長期線の傾き{k}営業日）"]

    # ---------- 1. 定義の確認 ----------
    chk = base[base.code.isin(["4507", "9433"]) & (base.date == base.date.max())]
    chk = chk[["code", "date", "close", "ma_s", "ma_m", "ma_l", "pattern", "slope"]].copy()
    chk["長期線20日前比%"] = [
        (base[(base.code == c)].set_index("date").ma_l.iloc[-1] /
         base[(base.code == c)].set_index("date").ma_l.iloc[-1 - k] - 1) * 100 for c in chk.code]
    chk["銘柄"] = chk.code.map(UNIVERSE)
    out.append("## 1-1. 塩野義・KDDI の分類確認（データ最終日の終値）\n\n" + md(chk.set_index("銘柄")))

    occ = base[base.pattern >= 0].groupby("group").agg(延べ日数=("code", "size"), 銘柄数=("code", "nunique"),
                                                        月数=("month", "nunique"))
    occ["全日に占める%"] = occ["延べ日数"] / len(base) * 100
    occ = occ.reindex(GROUP_ORDER)
    out.append(f"## 1-2. 各グループの発生回数（{s}/{m}/{l}日線, 傾き{k}日）\n\n" +
               f"全日（条件なし）: 延べ {len(base):,} 日, {base.code.nunique()} 銘柄, "
               f"{base.date.min().date()} 〜 {base.date.max().date()}\n\n" + md(occ, ".1f"))

    # ---------- 2. リターン ----------
    for H in HORIZONS:
        rows = {"条件なし（全日）": summarize(base, base, H)}
        for g in GROUP_ORDER:
            sub = base[base.group == g]
            rows[g] = summarize(sub, base, H)
            rows[g]["信頼性"] = reliability(rows[g].get("件数", 0), sub.month.nunique())
        t = pd.DataFrame(rows).T
        t.to_csv(DD / f"ret{H}.csv")
        out.append(f"## 2-{H}. エントリー後 {H} 日リターン（翌日始値→{H}営業日後終値）\n\n" + md(t))

    # MAE と MA 到達率
    rows = {}
    for g in ["条件なし（全日）"] + GROUP_ORDER:
        sub = base if g.startswith("条件なし") else base[base.group == g]
        r = {}
        for H in HORIZONS:
            r[f"最大下落幅 平均%({H}日)"] = sub[f"mae{H}"].mean() * 100
        r["最大下落幅 下位5%点(20日)"] = sub["mae20"].quantile(0.05) * 100
        r["最大下落幅 最悪(20日)"] = sub["mae20"].min() * 100
        for key, nm in (("s", "短期"), ("m", "中期"), ("l", "長期")):
            on = sub[sub[f"up_{key}"] == 1]
            for H in (5, 20):
                r[f"{nm}線到達%({H}日)"] = on[f"reach{H}_{key}"].mean() * 100 if len(on) else np.nan
        rows[g] = r
    t = pd.DataFrame(rows).T
    t.to_csv(DD / "mae_reach.csv")
    out.append("## 2-4. 最大下落幅と、株価の上にあった移動平均線への到達率\n\n"
               "到達率は、その線が株価の上にあった事例のみで計算（シグナル日の線の値に、その後の高値が届いたか）。\n\n" + md(t, ".1f"))

    # ---------- 3. 指数との比較 ----------
    for H in (10, 20):
        rows = {}
        for pref, nm in (("ex_n225", "対日経平均"), ("ex_topix", "対TOPIX")):
            rows[f"条件なし（全日）{nm}"] = summarize(base, base, H, pref)
        for g in GROUP_ORDER:
            sub = base[base.group == g]
            for pref, nm in (("ex_n225", "対日経平均"), ("ex_topix", "対TOPIX")):
                rows[f"{g} {nm}"] = summarize(sub, base, H, pref)
        t = pd.DataFrame(rows).T
        t.to_csv(DD / f"excess{H}.csv")
        out.append(f"## 3-{H}. 超過リターン（個別株{H}日リターン − 同期間の指数リターン）\n\n" + md(t))

    conds = {
        "日経平均 当日プラス": base.n225_day > 0, "日経平均 当日マイナス": base.n225_day < 0,
        "日経平均 25日線の上": base.n225_above25 == 1, "日経平均 25日線の下": base.n225_above25 == 0,
        "日経平均 5日線の上": base.n225_above5 == 1, "日経平均 5日線の下": base.n225_above5 == 0,
        "日経平均 75日線の上": base.n225_above75 == 1, "日経平均 75日線の下": base.n225_above75 == 0,
        "TOPIX 当日プラス": base.topix_day > 0, "TOPIX 当日マイナス": base.topix_day < 0,
        "TOPIX 25日線の上": base.topix_above25 == 1, "TOPIX 25日線の下": base.topix_above25 == 0,
    }
    for col, nm in (("ret20", "20日リターン 平均%"), ("ex_topix_20", "20日 対TOPIX超過 平均%")):
        tab = {}
        for g in ["条件なし（全日）"] + GROUP_ORDER:
            sub = base if g.startswith("条件なし") else base[base.group == g]
            tab[g] = {c: sub.loc[m.reindex(sub.index, fill_value=False), col].mean() * 100 for c, m in conds.items()}
        cnt = {g: {c: int(m.reindex((base if g.startswith('条件なし') else base[base.group == g]).index,
                                     fill_value=False).sum()) for c, m in conds.items()}
               for g in ["条件なし（全日）"] + GROUP_ORDER}
        t = pd.DataFrame(tab).T
        t.to_csv(DD / f"index_cond_{col}.csv")
        pd.DataFrame(cnt).T.to_csv(DD / "index_cond_counts.csv")
        out.append(f"## 3-cond. 指数の状態で分けた場合: {nm}\n\n" + md(t))
    out.append("### 3-cond. 件数\n\n" + md(pd.DataFrame(cnt).T, ".0f"))

    # ---------- 5. 足・出来高の条件 ----------
    r20 = pd.read_csv(DD / "ret20.csv", index_col=0)
    better = [g for g in GROUP_ORDER if r20.loc[g, "全日比 差%"] > 0]
    filt = {
        "出来高≥1.0倍": lambda d: d.vol_ratio >= 1.0, "出来高≥1.5倍": lambda d: d.vol_ratio >= 1.5,
        "出来高≥2.0倍": lambda d: d.vol_ratio >= 2.0, "出来高<1.0倍": lambda d: d.vol_ratio < 1.0,
        "下ヒゲ≥30%": lambda d: d.lower_shadow >= 0.3, "下ヒゲ≥50%": lambda d: d.lower_shadow >= 0.5,
        "下ヒゲ≥60%": lambda d: d.lower_shadow >= 0.6,
        "反転陽線(陽線かつ前日比+)": lambda d: d.bull == 1, "反転陽線なし": lambda d: d.bull == 0,
        "直近3本の実体≤0.5%": lambda d: d.body_max3 <= 0.005, "直近3本の実体≤1.0%": lambda d: d.body_max3 <= 0.01,
        "直近3本の実体≤1.5%": lambda d: d.body_max3 <= 0.015,
        "MACDヒスト縮小1日": lambda d: d.macd_rise_n >= 1, "MACDヒスト縮小2日連続": lambda d: d.macd_rise_n >= 2,
        "MACDヒスト縮小3日連続": lambda d: d.macd_rise_n >= 3,
        "反転陽線+出来高≥1.5倍": lambda d: (d.bull == 1) & (d.vol_ratio >= 1.5),
        "反転陽線+MACD縮小2日": lambda d: (d.bull == 1) & (d.macd_rise_n >= 2),
    }
    blocks = []
    for g in better:
        sub = base[base.group == g]
        rows = {"（条件なし）": summarize(sub, base, 20)}
        for fn, f in filt.items():
            s2 = sub[f(sub).fillna(False)]
            rows[fn] = summarize(s2, base, 20) if len(s2) else {}
            if len(s2):
                rows[fn]["グループ内比 差%"] = (s2.ret20.mean() - sub.ret20.mean()) * 100
                rows[fn]["信頼性"] = reliability(len(s2.ret20.dropna()), s2.month.nunique())
        t = pd.DataFrame(rows).T
        t.to_csv(DD / f"filters_{g.split()[0]}_{g.split('｜')[1]}.csv")
        keep = ["件数", "銘柄数", "平均%", "中央値%", "勝率%", "全日比 差%", "差CI下%", "差CI上%", "グループ内比 差%", "信頼性"]
        blocks.append(f"### {g}\n\n" + md(t[[c for c in keep if c in t.columns]]))
    out.append("## 5. 足・出来高の条件（20日リターン、全日平均を上回ったグループのみ）\n\n"
               f"対象グループ: {', '.join(better)}\n\n" + "\n\n".join(blocks))

    # ---------- 事例リスト ----------
    ev = base[base.ret20.notna() & base.group.isin(GROUP_ORDER)].copy()
    ev["name"] = ev.code.map(UNIVERSE)
    ev[["group", "code", "name", "date", "close", "ret5", "ret10", "ret20", "ex_topix_20", "mae20",
        "vol_ratio", "lower_shadow", "bull", "macd_rise_n"]].to_csv(DD / "events.csv", index=False)
    (RD / "tables.md").write_text("\n\n".join(out), encoding="utf-8")
    print(tag, "done", len(base))
    return base


def sensitivity(prices, idx) -> None:
    sens = {}
    settings = [((5, 25, 75), 20), ((5, 20, 60), 20), ((10, 25, 75), 20), ((25, 50, 75), 20),
                ((5, 25, 75), 10), ((5, 25, 75), 40), ((25, 50, 75), 10), ((25, 50, 75), 40)]
    for (s, m, l), k in settings:
        b = build(prices, idx, s, m, l, k)
        key = f"MA{s}/{m}/{l} 傾き{k}日"
        for g in GROUP_ORDER:
            r = summarize(b[b.group == g], b, 20)
            sens.setdefault(g, {})[f"{key} 差%"] = r.get("全日比 差%")
            sens[g][f"{key} 件数"] = r.get("件数")
            sens[g][f"{key} 差CI"] = f"[{r.get('差CI下%', np.nan):.2f}, {r.get('差CI上%', np.nan):.2f}]"
        print("sens", key)
    t = pd.DataFrame(sens).T
    t.to_csv(D / "sensitivity.csv")
    cols = [c for c in t.columns if c.endswith("差%")]
    txt = ("# 感度確認：20日リターンの全日比の差（%pt）\n\n" + md(t[cols].astype(float)) +
           "\n\n## 件数\n\n" + md(t[[c for c in t.columns if c.endswith('件数')]].astype(float), ".0f") +
           "\n\n## 差の95%CI（月クラスター・ブートストラップ）\n\n" + md(t[[c for c in t.columns if c.endswith('差CI')]]))
    (R / "sensitivity.md").write_text(txt, encoding="utf-8")


def main() -> None:
    prices = load_prices()
    idx = index_features(prices["^N225"], "n225").join(index_features(prices["1306.T"], "topix"), how="outer")
    run_setting(prices, idx, 5, 25, 75, 20, "base_5_25_75", "基本設定")
    run_setting(prices, idx, 25, 50, 75, 20, "app_25_50_75", "証券アプリ設定")
    sensitivity(prices, idx)


if __name__ == "__main__":
    main()
