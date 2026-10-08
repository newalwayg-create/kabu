"""コマンドライン:

  python -m kabu_corr collect  --start 2019-01-01      # データ収集のみ
  python -m kabu_corr analyze                          # 保存済みデータを分析
  python -m kabu_corr run      --start 2019-01-01      # 収集 + 分析
  python -m kabu_corr demo                             # 合成データで動作確認（ネット不要）
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .align import build_aligned
from .collect import collect, load_prices
from .report import build_report


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="kabu_corr", description="日経平均・先物・半導体株・SOX・ダウの相関分析")
    p.add_argument("command", choices=["collect", "analyze", "run", "demo"])
    p.add_argument("--start", default="2019-01-01", help="取得開始日 (YYYY-MM-DD)")
    p.add_argument("--end", default=None, help="取得終了日 (省略時は最新)")
    p.add_argument("--data", type=Path, default=Path("data/prices.csv"), help="価格CSVの保存先")
    p.add_argument("--out", type=Path, default=Path("output"), help="レポート出力先")
    p.add_argument("--window", type=int, default=60, help="ローリング相関の窓(営業日)")
    args = p.parse_args(argv)

    if args.command == "demo":
        from .synthetic import make_prices

        prices = make_prices()
        out = args.out if args.out != Path("output") else Path("output_demo")
    else:
        if args.command in ("collect", "run"):
            prices = collect(args.data, args.start, args.end)
            if args.command == "collect":
                return
        else:
            prices = load_prices(args.data)
        out = args.out

    path = build_report(build_aligned(prices), out, args.window)
    print(f"レポートを出力しました: {path}")


if __name__ == "__main__":
    main()
