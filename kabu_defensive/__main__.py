"""コマンドライン:

  python -m kabu_defensive run     --start 2019-01-01   # データ収集 + ランキング
  python -m kabu_defensive analyze                      # 保存済みデータでランキングだけ
"""

from __future__ import annotations

import argparse
from pathlib import Path

from kabu_corr.collect import download, load_prices

from .analysis import closes
from .config import UNIVERSE, all_tickers
from .report import build_report


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="kabu_defensive", description="ディフェンシブ銘柄のリスク回避度ランキング")
    p.add_argument("command", choices=["run", "analyze"])
    p.add_argument("--start", default="2019-01-01", help="取得開始日 (YYYY-MM-DD)")
    p.add_argument("--data", type=Path, default=Path("data/defensive_prices.csv"), help="価格CSVの保存先")
    p.add_argument("--out", type=Path, default=Path("output/defensive"), help="レポート出力先")
    p.add_argument("--top", type=int, default=50, help="ランキングに載せる銘柄数")
    args = p.parse_args(argv)

    if args.command == "run":
        prices = download(all_tickers(), args.start)
        args.data.parent.mkdir(parents=True, exist_ok=True)
        prices.to_csv(args.data, index=False)
    else:
        prices = load_prices(args.data)

    path = build_report(closes(prices), [s.ticker for s in UNIVERSE], args.out, args.top)
    print(f"レポートを出力しました: {path}")


if __name__ == "__main__":
    main()
