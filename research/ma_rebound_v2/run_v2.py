"""v2 検証の実行: 事例抽出 → 除外 → 樹形図 → エントリー/イグジット → 年別 → 表・図の出力."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from core import (D, HERE, PNAME, UNIVERSE, boot_diff, build_all, first_days, load_prices, period, stats,
                  stock_frame, topix_frame)
from exits import RULES, rule_name, simulate
from tree import MIN_N, Node, flatten, grow

R = HERE / "results"
R.mkdir(exist_ok=True)
EXCL = {"除外なし": None, "TOPIX20日−5%以下を除外": -0.05, "TOPIX20日−7.5%以下を除外": -0.075,
        "TOPIX20日−10%以下を除外": -0.10}
ORDER = [f"{p}_{s}" for p in range(1, 8) for s in ("上向き", "下向き")] + ["0_上向き", "0_下向き"]


def md(df, f=".2f"):
    return df.to_markdown(floatfmt=f)


def sname(state):
    p, s = state.split("_")
    return f"{PNAME[int(p)]}｜{s}"


def excl(df, thr):
    return df if thr is None else df[~(df.tpx_ret20_past <= thr)]


def main():
    prices = load_prices()
    out = []
    alld, ev = build_all(prices, gap=3)
    ex_all, te_all = period(alld, "探索"), period(alld, "検証")
    ex_ev, te_ev = period(ev, "探索"), period(ev, "検証")

    # ---------- 事例の数え方（gap 感度） ----------
    rows = []
    for g in (0, 3, 5, 10):
        e = ev if g == 3 else build_all(prices, gap=g)[1]
        rows.append({"中断の許容日数": g, "探索 事例数": period(e, "探索").ret20.notna().sum(), "検証 事例数": period(e, "検証").ret20.notna().sum(),
                     "探索 全日数": len(ex_all), "P7下向き 探索 平均%": period(e, "探索").query("state=='7_下向き'").ret20.mean() * 100,
                     "P4上向き 探索 平均%": period(e, "探索").query("state=='4_上向き'").ret20.mean() * 100})
    out.append("## A. 事例の数え方：条件から外れた日数の許容（gap）を変えた場合\n\n"
               "gap=3（採用）: 同じ状態から外れて3営業日以内に戻った場合は同一事例として扱い、4営業日以上外れてから戻った場合は新しい事例とする。\n\n"
               + md(pd.DataFrame(rows).set_index("中断の許容日数")))

    # ---------- 基準 ----------
    base = pd.DataFrame({"探索 全日": stats(ex_all), "検証 全日": stats(te_all),
                         "探索 全事例(初日のみ)": stats(ex_ev), "検証 全事例(初日のみ)": stats(te_ev)}).T
    out.append("## B. 比較の基準（条件なし）: 20日リターン（翌日寄付→20営業日後終値）\n\n" + md(base))

    # ---------- 除外 ----------
    rows = []
    for nm, thr in EXCL.items():
        a, b = excl(ex_ev, thr), excl(te_ev, thr)
        rows.append({"除外条件": nm, "探索 事例数": len(a), "探索 除外数": len(ex_ev) - len(a),
                     "検証 事例数": len(b), "検証 除外数": len(te_ev) - len(b),
                     **{f"探索 {k}": v for k, v in stats(a).items() if k in ("上昇割合%", "平均%", "対TOPIX超過%")},
                     **{f"検証 {k}": v for k, v in stats(b).items() if k in ("上昇割合%", "平均%", "対TOPIX超過%")}})
    out.append("## C. 外部環境による暴落の除外（エントリー日のTOPIX〔1306〕直近20営業日騰落率で判定）\n\n"
               + md(pd.DataFrame(rows).set_index("除外条件")))

    # ---------- 第1・第2階層 ----------
    lv = {}
    for st in ORDER:
        for nm, thr in EXCL.items():
            a, b = excl(ex_ev[ex_ev.state == st], thr), excl(te_ev[te_ev.state == st], thr)
            sa, sb = stats(a), stats(b)
            lo, hi = boot_diff(a, excl(ex_all, thr), "ret20")
            lv[(sname(st), nm)] = {"探索 件数": sa["件数"], "探索 上昇%": sa["上昇割合%"], "探索 平均%": sa["平均%"],
                                   "探索 超過%": sa["対TOPIX超過%"], "探索 全日比 差CI": f"[{lo:+.2f}, {hi:+.2f}]",
                                   "検証 件数": sb["件数"], "検証 上昇%": sb["上昇割合%"], "検証 平均%": sb["平均%"],
                                   "検証 超過%": sb["対TOPIX超過%"]}
    t = pd.DataFrame(lv).T
    t.to_csv(D / "level12.csv")
    t0 = t.xs("除外なし", level=1)
    out.append("## D. 第1・第2階層（パターン × 75日線の傾き）、除外なし\n\n"
               f"基準（全日）: 探索 平均 {base.loc['探索 全日','平均%']:.2f}% / 上昇 {base.loc['探索 全日','上昇割合%']:.1f}% / 超過 {base.loc['探索 全日','対TOPIX超過%']:.2f}%、"
               f"検証 平均 {base.loc['検証 全日','平均%']:.2f}% / 上昇 {base.loc['検証 全日','上昇割合%']:.1f}% / 超過 {base.loc['検証 全日','対TOPIX超過%']:.2f}%\n\n"
               + md(t0))
    out.append("### D-2. 除外条件別（全条件）\n\n" + md(t))

    # ---------- 樹形図 ----------
    # 第3階層での要素ごとの差（全ノード平均）から、分岐の順番を決める（探索期間のみ）
    pre = []
    for st in ORDER:
        exs = ex_ev[ex_ev.state == st]
        if len(exs.ret20.dropna()) >= 2 * MIN_N:
            from tree import rank_splits
            k = rank_splits(exs, int(st.split("_")[0]), set())
            pre.append(k[k["両側100件以上"]].groupby("要素")["|差|"].max())
    fam_order = pd.concat(pre, axis=1).mean(axis=1).sort_values(ascending=False)
    ORDER_F = list(fam_order.index)
    out.append("## E-0. 分岐の順番（探索期間、第3階層候補での |平均の差| の全ノード平均, pt）\n\n"
               + md(fam_order.to_frame("平均 |差| pt")) + f"\n\n→ 樹形図は {' → '.join(ORDER_F[:3])} の順で分岐（各段で、その要素の中で差が最大の閾値を採用）。")
    trees, flat, ranks = {}, [], []
    for st in ORDER:
        p = int(st.split("_")[0])
        exs, tes = ex_ev[ex_ev.state == st], te_ev[te_ev.state == st]
        root = Node(label=sname(st))
        grow(root, exs, tes, p, set(), 0, 3, stats, ORDER_F)
        trees[st] = root
        for r in flatten(root):
            flat.append({"第2階層": sname(st), **r})
        if root.split_rank is not None:
            rk = root.split_rank.copy()
            rk.insert(0, "第2階層", sname(st))
            ranks.append(rk)
    fl = pd.DataFrame(flat)
    fl.to_csv(D / "tree_nodes.csv", index=False)
    rk = pd.concat(ranks)
    rk.to_csv(D / "split_rank_level3.csv", index=False)
    # 要素ごとの平均的な差の大きさ（第3階層候補, 両側100件以上のもの）
    fam = rk[rk["両側100件以上"]].groupby(["第2階層", "要素"])["|差|"].max().unstack()
    fam.loc["（平均）"] = fam.mean()
    out.append("## E. 第3階層：どの要素で分けると差が大きいか（探索期間、各要素の最良の閾値での |平均の差| pt）\n\n"
               "各第2階層ノードで、該当/非該当の両側に100件以上ある分け方だけを比較。空欄は両側100件を満たす分け方がない。\n\n"
               + md(fam, ".2f"))
    out.append("### E-2. 第3階層の分岐候補 全一覧（探索期間）\n\n" + md(rk.drop(columns=["|差|"]).set_index("第2階層"), ".2f"))
    show = ["第2階層", "深さ", "枝", "探索 件数", "探索 上昇割合%", "探索 平均%", "探索 対TOPIX超過%",
            "検証 件数", "検証 上昇割合%", "検証 平均%", "検証 対TOPIX超過%", "注記"]
    out.append("## F. 樹形図の各枝（探索で分岐を決定 → 検証に同じ定義を適用）\n\n" + md(fl[show].set_index("第2階層")))

    # ---------- 成績の良い枝の選定（探索のみ） ----------
    bex = base.loc["探索 全日"]
    cand = fl[(fl["探索 件数"] >= MIN_N)].copy()
    cand["探索 平均差"] = cand["探索 平均%"] - bex["平均%"]
    cand["探索 上昇差"] = cand["探索 上昇割合%"] - bex["上昇割合%"]
    good = cand[(cand["探索 平均差"] > 0) & (cand["探索 上昇差"] > 0) & (cand["探索 対TOPIX超過%"] > bex["対TOPIX超過%"])]
    good = good.sort_values("探索 平均%", ascending=False).head(6)
    sel = [(r["第2階層"], r["枝"]) for _, r in good.iterrows()]
    for must in ("P7 3本すべて上｜下向き", "P4 25+50日｜上向き"):  # 塩野義型・KDDI型は必ず含める
        if (must, "(第2階層)") not in sel:
            sel.append((must, "(第2階層)"))

    def branch_events(df, l2, branch):
        st = [s for s in ORDER if sname(s) == l2][0]
        node = trees[st]
        if branch != "(第2階層)":
            for part in branch.split(" → "):
                node = [c for c in node.children if c.label == part][0]
        from tree import apply_path
        return apply_path(df[df.state == st], node.path)

    # 探索/検証 並べた表 + 検証で落ちたか
    rows = []
    for l2, br in sel:
        a, b = branch_events(ex_ev, l2, br), branch_events(te_ev, l2, br)
        sa, sb = stats(a), stats(b)
        lo, hi = boot_diff(a, ex_all, "ret20")
        lo2, hi2 = boot_diff(b, te_all, "ret20")
        bte = base.loc["検証 全日"]
        dropped = []
        if sb["件数"] < MIN_N:
            dropped.append("検証の事例が100件未満")
        if not (sb["平均%"] > bte["平均%"]):
            dropped.append("平均が全日以下")
        if not (sb["上昇割合%"] > bte["上昇割合%"]):
            dropped.append("上昇割合が全日以下")
        if not (sb["対TOPIX超過%"] > bte["対TOPIX超過%"]):
            dropped.append("超過が全日以下")
        rows.append({"第2階層": l2, "枝": br,
                     "探索 件数": sa["件数"], "探索 上昇%": sa["上昇割合%"], "探索 平均%": sa["平均%"],
                     "探索 超過%": sa["対TOPIX超過%"], "探索 全日比差CI": f"[{lo:+.2f}, {hi:+.2f}]",
                     "検証 件数": sb["件数"], "検証 上昇%": sb["上昇割合%"], "検証 平均%": sb["平均%"],
                     "検証 超過%": sb["対TOPIX超過%"], "検証 全日比差CI": f"[{lo2:+.2f}, {hi2:+.2f}]",
                     "検証での判定": "維持" if not dropped else "低下: " + "・".join(dropped)})
    comp = pd.DataFrame(rows)
    comp.to_csv(D / "explore_vs_test.csv", index=False)
    out.append("## G. 探索期間で選んだ枝の、探索 vs 検証（20日・翌日寄付エントリー）\n\n"
               f"基準（全日）: 探索 平均 {bex['平均%']:.2f}% / 上昇 {bex['上昇割合%']:.1f}% / 超過 {bex['対TOPIX超過%']:.2f}%、"
               f"検証 平均 {base.loc['検証 全日','平均%']:.2f}% / 上昇 {base.loc['検証 全日','上昇割合%']:.1f}% / 超過 {base.loc['検証 全日','対TOPIX超過%']:.2f}%\n\n"
               "選定基準（探索のみ）: 100件以上、かつ平均・上昇割合・対TOPIX超過のすべてが全日を上回る枝を平均の高い順に最大6本＋塩野義型・KDDI型の第2階層。\n\n"
               + md(comp.set_index("第2階層")))

    # 除外条件別（選定枝）
    rows = []
    for l2, br in sel:
        for nm, thr in EXCL.items():
            a, b = excl(branch_events(ex_ev, l2, br), thr), excl(branch_events(te_ev, l2, br), thr)
            sa, sb = stats(a), stats(b)
            rows.append({"枝": f"{l2} / {br}", "除外": nm, "探索 件数": sa["件数"], "探索 上昇%": sa["上昇割合%"],
                         "探索 平均%": sa["平均%"], "検証 件数": sb["件数"], "検証 上昇%": sb["上昇割合%"],
                         "検証 平均%": sb["平均%"]})
    out.append("### G-2. 選定枝 × 除外条件\n\n" + md(pd.DataFrame(rows).set_index("枝")))

    # ---------- 年別 ----------
    rows = []
    for l2, br in [("（全日）", "")] + sel:
        src = alld if l2 == "（全日）" else pd.concat([branch_events(ex_ev, l2, br), branch_events(te_ev, l2, br)])
        if l2 == "（全日）":
            src = pd.concat([ex_all, te_all])
        g = src.groupby(src.date.dt.year)
        for y, x in g:
            s = stats(x)
            rows.append({"枝": "（全日）" if l2 == "（全日）" else f"{l2} / {br}", "年": y, "件数": s["件数"],
                         "上昇%": s["上昇割合%"], "平均%": s["平均%"], "超過%": s["対TOPIX超過%"]})
    yr = pd.DataFrame(rows)
    yr.to_csv(D / "yearly.csv", index=False)
    piv = yr.pivot_table(index="枝", columns="年", values=["平均%"]).round(2)
    pivn = yr.pivot_table(index="枝", columns="年", values=["件数"])
    pivw = yr.pivot_table(index="枝", columns="年", values=["上昇%"]).round(1)
    out.append("## H. 年ごとの内訳（20日・翌日寄付）\n\n### 平均%\n\n" + md(piv) + "\n\n### 上昇割合%\n\n" + md(pivw, ".1f")
               + "\n\n### 件数\n\n" + md(pivn, ".0f") +
               "\n\n※ 2020年は6月以降、2024年は探索期間の結果漏れ防止のため12/2まで、2026年は9月中旬まで（20日後の結果が必要なため）。")

    # ---------- エントリー / イグジット ----------
    tpx = topix_frame(prices)
    arrays, pos = {}, {}
    for code in UNIVERSE:
        if code not in prices:
            continue
        f = stock_frame(prices[code], tpx)
        arrays[code] = {k: f[k].to_numpy() for k in ("open", "high", "low", "close", "ma25", "ma50", "ma75")}
        pos[code] = {d: i for i, d in enumerate(f.index)}
    sim_rows = []
    for l2, br in sel:
        for per, src in (("探索", ex_ev), ("検証", te_ev)):
            evs = branch_events(src, l2, br)
            for entry in ("引け", "寄付"):
                for rule in RULES:
                    res = [simulate(arrays[r.code], pos[r.code][r.date], entry, rule) for r in evs.itertuples()]
                    res = [x for x in res if x is not None]
                    if not res:
                        sim_rows.append({"枝": f"{l2} / {br}", "期間": per, "エントリー": entry, "ルール": rule_name(rule), "件数": 0})
                        continue
                    a = np.array(res)
                    sim_rows.append({"枝": f"{l2} / {br}", "期間": per, "エントリー": entry, "ルール": rule_name(rule),
                                     "件数": len(a), "平均%": a[:, 0].mean() * 100, "勝率%": (a[:, 0] > 0).mean() * 100,
                                     "最大下落 平均%": a[:, 2].mean() * 100, "最大下落 最悪%": a[:, 2].min() * 100,
                                     "平均保有日数": a[:, 1].mean()})
    sim = pd.DataFrame(sim_rows)
    sim.to_csv(D / "exit_rules.csv", index=False)
    # 探索で最良（平均%最大, 件数≥100）のルールを選び、検証と比較
    best_rows = []
    for br, g in sim.groupby("枝", sort=False):
        e = g[(g.期間 == "探索") & (g.件数 >= MIN_N)]
        if e.empty:
            continue
        b = e.sort_values("平均%", ascending=False).iloc[0]
        t_ = g[(g.期間 == "検証") & (g.エントリー == b.エントリー) & (g.ルール == b.ルール)].iloc[0]
        ref_e = g[(g.期間 == "探索") & (g.エントリー == "寄付") & (g.ルール == "固定20日")].iloc[0]
        ref_t = g[(g.期間 == "検証") & (g.エントリー == "寄付") & (g.ルール == "固定20日")].iloc[0]
        rank_t = g[(g.期間 == "検証") & (g.件数 > 0)].sort_values("平均%", ascending=False).reset_index(drop=True)
        rk_ = int(rank_t.index[(rank_t.エントリー == b.エントリー) & (rank_t.ルール == b.ルール)][0]) + 1
        bte = base.loc["検証 全日"]
        if t_["件数"] < MIN_N:
            judge = "判定保留（検証の事例が100件未満）"
        elif t_["平均%"] > bte["平均%"] and t_["平均%"] >= ref_t["平均%"]:
            judge = "維持"
        else:
            judge = "低下"
        best_rows.append({"枝": br, "探索で選んだルール": f"{b.エントリー}・{b.ルール}",
                          "探索 件数": b["件数"], "探索 平均%": b["平均%"], "探索 勝率%": b["勝率%"],
                          "探索 最大下落平均%": b["最大下落 平均%"], "探索 保有日数": b["平均保有日数"],
                          "検証 件数": t_["件数"], "検証 平均%": t_["平均%"], "検証 勝率%": t_["勝率%"],
                          "検証 最大下落平均%": t_["最大下落 平均%"], "検証 保有日数": t_["平均保有日数"],
                          "検証での順位": rk_, "比較ルール数": len(rank_t),
                          "参考 寄付・固定20日 探索 平均%": ref_e["平均%"], "参考 寄付・固定20日 検証 平均%": ref_t["平均%"],
                          "検証での判定": judge})
    bt = pd.DataFrame(best_rows)
    bt.to_csv(D / "exit_best.csv", index=False)
    out.append("## I. エントリー・イグジット：探索期間で最良のルールを選び、検証期間で確認\n\n"
               "最良 = 探索期間の平均リターンが最大（件数100以上、30ルール＝エントリー2通り×イグジット15通りから選択）。\n判定「維持」= 検証期間の平均が、検証期間の全日平均（翌日寄付・20日）を上回り、かつ参考ルール（寄付・固定20日）以上。検証の事例が100件未満なら判定保留。\n\n"
               + md(bt.set_index("枝")))
    for br, g in sim.groupby("枝", sort=False):
        t = g.pivot_table(index=["エントリー", "ルール"], columns="期間",
                          values=["件数", "平均%", "勝率%", "最大下落 平均%", "平均保有日数"], sort=False)
        out.append(f"### I-詳細: {br}\n\n" + md(t))
    (R / "tables_v2.md").write_text("\n\n".join(out), encoding="utf-8")
    json.dump({st: _tree_json(n) for st, n in trees.items()}, open(D / "trees.json", "w"), ensure_ascii=False, default=float)
    json.dump({"base": base.to_dict(), "sel": sel}, open(D / "meta.json", "w"), ensure_ascii=False, default=float)
    print("done")


def _tree_json(n: Node):
    return {"label": n.label, "ex": n.stats_ex, "te": n.stats_te, "note": n.note,
            "children": [_tree_json(c) for c in n.children]}


if __name__ == "__main__":
    main()
