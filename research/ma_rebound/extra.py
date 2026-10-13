"""追加の頑健性チェック: 期間による安定性（年別・前後半）."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
D = HERE / "data"
KEY = ["P7 3本すべて上｜下向き", "P7 3本すべて上｜上向き", "P4 短期+中期｜上向き", "P4 短期+中期｜下向き",
       "P6 中期+長期｜下向き", "P3 長期のみ上｜上向き", "G0 3本すべて下(株価が上)｜下向き"]


def run(tag: str) -> str:
    ev = pd.read_csv(D / tag / "events.csv", parse_dates=["date"], dtype={"code": str},
                     usecols=["group", "code", "date", "ret20", "ex_topix_20"])
    ev["year"] = ev.date.dt.year
    ev["half"] = ev.date.dt.year.map(lambda y: "2016-2020" if y <= 2020 else "2021-2026")
    out = [f"## {tag}：年別・前後半の安定性（20日リターン, 全日平均との差 %pt）"]
    for unit in ("half", "year"):
        base = ev.groupby(unit).agg(base_ret=("ret20", "mean"), base_ex=("ex_topix_20", "mean"))
        rows = {}
        for g in KEY:
            sub = ev[ev.group.str.startswith(g.split("｜")[0].split()[0]) & ev.group.str.endswith(g.split("｜")[1])]
            sub = ev[ev.group.str.contains(g.split()[0] + " ", regex=False) & ev.group.str.endswith(g.split("｜")[1])]
            a = sub.groupby(unit).agg(n=("ret20", "size"), ret=("ret20", "mean"), ex=("ex_topix_20", "mean"))
            a = a.join(base)
            rows[(g, "絶対 差")] = (a.ret - a.base_ret) * 100
            rows[(g, "対TOPIX超過 差")] = (a.ex - a.base_ex) * 100
            rows[(g, "件数")] = a.n
        t = pd.DataFrame(rows).T
        out.append(f"### 単位: {'前後半' if unit == 'half' else '年'}\n\n" + t.to_markdown(floatfmt=".2f"))
    return "\n\n".join(out)


if __name__ == "__main__":
    txt = "# 期間による安定性\n\n" + run("base_5_25_75") + "\n\n" + run("app_25_50_75")
    (HERE / "results" / "stability.md").write_text(txt, encoding="utf-8")
    print(txt[:8000])
