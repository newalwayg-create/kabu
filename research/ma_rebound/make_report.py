"""要約表を CSV から自動生成（数値の転記ミス防止）→ results/summary_tables.md"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
D = HERE / "data"
TAGS = {"base_5_25_75": "基本 5/25/75", "app_25_50_75": "アプリ 25/50/75"}


def ci(lo, hi):
    return f"[{lo:+.2f}, {hi:+.2f}]"


def flag(lo, hi):
    return "＋（有意）" if lo > 0 else ("−（有意）" if hi < 0 else "差なし")


def ret_table(H: int) -> str:
    parts = []
    for tag, nm in TAGS.items():
        r = pd.read_csv(D / tag / f"ret{H}.csv", index_col=0)
        e = pd.read_csv(D / tag / f"excess{H}.csv", index_col=0) if H in (10, 20) else None
        rows = []
        for g, x in r.iterrows():
            row = {"グループ": g, "件数": int(x["件数"]), "平均%": x["平均%"], "中央値%": x["中央値%"],
                   "勝率%": x["勝率%"]}
            if not g.startswith("条件なし"):
                row["全日比 差pt [95%CI]"] = f"{x['全日比 差%']:+.2f} {ci(x['差CI下%'], x['差CI上%'])}"
                row["判定(絶対)"] = flag(x["差CI下%"], x["差CI上%"])
                if e is not None:
                    ex = e.loc[f"{g} 対TOPIX"]
                    row["対TOPIX超過 平均%"] = ex["平均%"]
                    row["超過の全日比 差pt [95%CI]"] = f"{ex['全日比 差%']:+.2f} {ci(ex['差CI下%'], ex['差CI上%'])}"
                    row["判定(超過)"] = flag(ex["差CI下%"], ex["差CI上%"])
                row["信頼性"] = x["信頼性"]
            elif e is not None:
                row["対TOPIX超過 平均%"] = e.loc["条件なし（全日）対TOPIX", "平均%"]
            rows.append(row)
        t = pd.DataFrame(rows).set_index("グループ")
        parts.append(f"#### {nm}\n\n" + t.to_markdown(floatfmt=".2f"))
    return "\n\n".join(parts)


def occ_table() -> str:
    cols = {}
    for tag, nm in TAGS.items():
        r = pd.read_csv(D / tag / "ret20.csv", index_col=0)
        cols[f"{nm} 件数(20日リターン算出可)"] = r["件数"].astype(int)
        cols[f"{nm} 銘柄数"] = r["銘柄数"].astype(int)
    return pd.DataFrame(cols).to_markdown()


def mae_reach() -> str:
    parts = []
    for tag, nm in TAGS.items():
        t = pd.read_csv(D / tag / "mae_reach.csv", index_col=0)
        keep = ["最大下落幅 平均%(20日)", "最大下落幅 下位5%点(20日)", "最大下落幅 最悪(20日)",
                "短期線到達%(5日)", "短期線到達%(20日)", "中期線到達%(5日)", "中期線到達%(20日)",
                "長期線到達%(5日)", "長期線到達%(20日)"]
        parts.append(f"#### {nm}\n\n" + t[keep].to_markdown(floatfmt=".1f"))
    return "\n\n".join(parts)


def index_cond() -> str:
    parts = []
    cols = ["日経平均 当日プラス", "日経平均 当日マイナス", "日経平均 5日線の上", "日経平均 5日線の下",
            "日経平均 25日線の上", "日経平均 25日線の下", "日経平均 75日線の上", "日経平均 75日線の下",
            "TOPIX 当日プラス", "TOPIX 当日マイナス", "TOPIX 25日線の上", "TOPIX 25日線の下"]
    for tag, nm in TAGS.items():
        a = pd.read_csv(D / tag / "index_cond_ret20.csv", index_col=0)[cols]
        b = pd.read_csv(D / tag / "index_cond_ex_topix_20.csv", index_col=0)[cols]
        n = pd.read_csv(D / tag / "index_cond_counts.csv", index_col=0)[cols]
        parts.append(f"#### {nm}：20日リターン平均%\n\n" + a.to_markdown(floatfmt=".2f") +
                     f"\n\n#### {nm}：20日 対TOPIX超過 平均%\n\n" + b.to_markdown(floatfmt=".2f") +
                     f"\n\n#### {nm}：件数\n\n" + n.to_markdown(floatfmt=".0f"))
    return "\n\n".join(parts)


def filters() -> str:
    parts = []
    for tag, nm in TAGS.items():
        for f in sorted((D / tag).glob("filters_*.csv")):
            t = pd.read_csv(f, index_col=0)
            keep = [c for c in ["件数", "平均%", "勝率%", "全日比 差%", "差CI下%", "差CI上%", "グループ内比 差%", "信頼性"] if c in t]
            g = f.stem.replace("filters_", "").replace("_", "｜")
            parts.append(f"#### {nm}：{g}\n\n" + t[keep].to_markdown(floatfmt=".2f"))
    return "\n\n".join(parts)


def main():
    fetch = pd.read_csv(D / "fetch_log.csv", dtype={"code": str})
    failed = fetch[fetch.status == "FAILED"]
    adj = fetch[fetch.status.str.startswith("ADJUSTED")]
    txt = ["# 要約表（自動生成）",
           "## 取得に失敗した銘柄\n\n" + failed[["code", "name", "status"]].to_markdown(index=False),
           "## 取得データの補正\n\n" + adj[["code", "name", "status"]].to_markdown(index=False),
           "## 発生回数\n\n" + occ_table(),
           "## 5日リターン\n\n" + ret_table(5),
           "## 10日リターン\n\n" + ret_table(10),
           "## 20日リターン（＋対TOPIX超過）\n\n" + ret_table(20),
           "## 最大下落幅とMA到達率\n\n" + mae_reach(),
           "## 指数の状態で分けた結果\n\n" + index_cond(),
           "## 足・出来高の条件\n\n" + filters()]
    (HERE / "results" / "summary_tables.md").write_text("\n\n".join(txt), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
