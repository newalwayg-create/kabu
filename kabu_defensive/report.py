"""ディフェンシブ銘柄ランキングの Markdown レポートと CSV の出力。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import analysis as A
from .config import SECTOR_NOTE, STRESS_PERIODS, by_ticker

TYPE_NOTE = {
    "全天候型": "5局面のうち3つ以上で ◎/○。迷ったらこのグループ",
    "下落相場型": "じわじわ下げる相場（月次で TOPIX がマイナスの月）で特に強い",
    "暴落耐性型": "数日〜数週間の急落（ショック安）で下げが小さい",
    "円高耐性型": "円高で相対的に買われる内需・輸入型",
    "金利上昇耐性型": "国内金利の上昇局面でも崩れにくい（金利上昇が業績・資産価値の追い風になる）",
    "インフレ耐性型": "原油など資源価格の上昇局面で相対的に強い",
}


def ranking(close: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    m = A.stock_metrics(close, tickers)
    m["score"] = A.risk_aversion_score(m)
    out = m.join(A.regime_strength(m)).sort_values("score", ascending=False)
    meta = by_ticker()
    out.insert(0, "name", [meta[t].name for t in out.index])
    out.insert(1, "sector", [meta[t].sector for t in out.index])
    out.insert(2, "rank", range(1, len(out) + 1))
    return out


def _pct(v: float, digits: int = 1) -> str:
    return f"{v * 100:+.{digits}f}%" if pd.notna(v) else "-"


def _code(t: str) -> str:
    return t.removesuffix(".T")


def build_report(close: pd.DataFrame, tickers: list[str], out_dir: Path, top: int = 50) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    r = ranking(close, tickers)
    r.to_csv(out_dir / "defensive_ranking.csv", encoding="utf-8-sig")
    t = r.head(top)
    marks = [f"mark:{x}" for x in A.REGIMES]
    start, end = close.index[0].date(), close.index[-1].date()
    lines = [
        f"# ディフェンシブ銘柄 リスク回避度ランキング TOP{top}",
        "",
        f"- 期間: {start} 〜 {end}（週次・月次リターン、配当は株価調整済みの値に含まず）",
        "- ベンチマーク: TOPIX（TOPIX連動ETF `1306` で代用）",
        f"- 対象: ディフェンシブ業種の候補 {len(tickers)} 銘柄のうち、3年以上のデータがある {len(r)} 銘柄を採点",
        "",
        "## リスク回避度スコアの算出方法（0〜100、高いほど守りが固い）",
        "",
        "候補内での順位（パーセンタイル）を重み付き平均したものです。",
        "",
        "| 指標 | 意味 | 重み |",
        "|---|---|---|",
        "| β（ベータ） | TOPIX が 1% 動いたときに何%動くか（週次）。低いほど良い | 25% |",
        "| 下方キャプチャ | TOPIX が下げた月に、その下げの何割を被ったか。マイナスは「市場が下げた月に上がった」 | 25% |",
        "| 急落時の超過リターン | 下記4回のショック安での対TOPIX超過リターン平均 | 20% |",
        "| ボラティリティ | 年率換算の値動きの大きさ | 15% |",
        "| 最大ドローダウン | 期間中の高値からの最大下落率 | 15% |",
        "",
        "急落局面: " + "、".join(f"{n}（{s}〜{e}）" for n, s, e in STRESS_PERIODS),
        "",
        "## 相場局面の判定方法",
        "",
        "| 局面 | 判定に使う値 | ◎ | ○ | △ | × |",
        "|---|---|---|---|---|---|",
        "| 下落相場 | TOPIX が下げた月の対TOPIX超過リターン | 候補内で上位16% | 候補内平均以上 | プラスだが平均未満 | マイナス |",
        "| 急落局面 | 急落4回の対TOPIX超過リターン平均 | 同上 | 同上 | 同上 | 同上 |",
        "| 円高 | 市場要因を除いたドル円への感応度（ドル円下落=円高でプラスなら強い） | t値≥2 | t値≥1 | 有意でないプラス | マイナス |",
        "| 金利上昇 | 市場要因を除いた「銀行株の対TOPIX超過」への感応度（国内金利上昇の代理） | 同上 | 同上 | 同上 | 同上 |",
        "| 資源高・インフレ | 市場要因を除いた ブレント原油への感応度 | 同上 | 同上 | 同上 | 同上 |",
        "",
        "円高・金利上昇・資源高は、TOPIX・ドル円・銀行株超過・原油の4つを同時に入れた週次の重回帰で測っています。"
        "単純に「円高の月の成績」を見ると、円高月は株安の月と重なりやすいため、ディフェンシブ株がどれも強く見えてしまうからです。",
        "",
        "タイプ: ◎/○ が3局面以上なら **全天候型**、それ以外は最も強い局面の名前で分類しています。",
        "",
        "## ランキング",
        "",
        "| 順位 | コード | 銘柄 | 業種 | スコア | β | 下方キャプチャ | 上方キャプチャ | 年率ボラ | 最大DD | 急落時超過 | "
        + " | ".join(A.REGIMES)
        + " | タイプ |",
        "|" + "---|" * (12 + len(A.REGIMES)),
    ]
    for tk, x in t.iterrows():
        lines.append(
            f"| {x['rank']} | {_code(tk)} | {x['name']} | {x['sector']} | **{x['score']:.1f}** | {x['beta']:.2f} | "
            f"{x['down_capture']:.2f} | {x['up_capture']:.2f} | {x['vol'] * 100:.0f}% | {x['max_dd'] * 100:.0f}% | "
            f"{_pct(x['stress_excess'])} | " + " | ".join(x[m] for m in marks) + f" | {x['type']} |"
        )

    lines += ["", "## タイプ別まとめ（TOP{0} 内）".format(top), ""]
    for typ, note in TYPE_NOTE.items():
        g = t[t["type"] == typ]
        if g.empty:
            continue
        names = "、".join(f"{x['name']}({_code(tk)}, {x['score']:.0f})" for tk, x in g.iterrows())
        lines += [f"### {typ}（{len(g)}銘柄）", "", f"{note}。", "", names, ""]

    lines += ["## 相場別のおすすめ（TOP{0} 内で ◎・○ の銘柄、強い順）".format(top), ""]
    for reg in A.REGIMES:
        parts = []
        for mk in ("◎", "○"):
            g = t[t[f"mark:{reg}"] == mk].sort_values(f"z:{reg}", ascending=False)
            if not g.empty:
                parts.append(f"{mk} " + "、".join(f"{x['name']}({_code(tk)})" for tk, x in g.iterrows()))
        lines += [f"- **{reg}**: " + (" / ".join(parts) or "該当なし")]
    lines += [
        "",
        "資源高・インフレ局面では、ほとんどのディフェンシブ銘柄が原材料・燃料コスト増で市場に劣後します。"
        "この局面への備えは、ディフェンシブ株よりも商社・資源株などで考えるのが基本です。",
    ]

    lines += [
        "",
        "## 急落局面ごとの対TOPIX超過リターン（TOP{0}）".format(top),
        "",
        "| コード | 銘柄 | " + " | ".join(n for n, _, _ in STRESS_PERIODS) + " |",
        "|" + "---|" * (2 + len(STRESS_PERIODS)),
    ]
    for tk, x in t.iterrows():
        lines.append(
            f"| {_code(tk)} | {x['name']} | " + " | ".join(_pct(x[f'stress:{n}']) for n, _, _ in STRESS_PERIODS) + " |"
        )

    lines += [
        "",
        "## 局面感応度の数値（TOP{0}）".format(top),
        "",
        "市場の動きを除いたうえで、各ファクターが 1% 動いたときのその銘柄の追加リターン(%)。カッコ内は t 値。"
        "下落相場は TOPIX が下げた月の対TOPIX超過リターン(月平均)。",
        "",
        "| コード | 銘柄 | 下落月の超過 | 円高 | 金利上昇 | 資源高 |",
        "|---|---|---|---|---|---|",
    ]
    for tk, x in t.iterrows():
        cells = [f"{x[f'sens:{f}']:+.2f} ({x[f'sens_t:{f}']:+.1f})" for f in ("円高", "金利上昇", "資源高・インフレ")]
        lines.append(f"| {_code(tk)} | {x['name']} | {_pct(x['regime:下落相場'])} | " + " | ".join(cells) + " |")

    lines += ["", "## 業種ごとの性格", "", "| 業種 | 景気に強い理由・弱点 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in SECTOR_NOTE.items() if k in set(t["sector"])]

    lines += [
        "",
        "## 注意",
        "",
        "- スコアは候補内の相対評価です。過去の値動きから計算しており、将来の下落耐性を保証しません。",
        "- 配当は含めていません（株価は分割調整のみ）。高配当銘柄は実際のトータルリターンがこれより良くなります。",
        "- 「金利上昇」は日本国債利回りが取得できないため、銀行株の対TOPIX超過リターンを代理指標にしています。",
        "- 上方キャプチャが低い銘柄は、上昇相場で TOPIX に置いていかれやすい点に注意（守りが固い裏返し）。",
        "- 個別要因（不祥事・TOB・薬の特許切れなど）による値動きも統計に含まれます。",
        "",
    ]
    path = out_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
