"""分析対象の銘柄定義。

market:
    "JP" … 東京市場の時間帯（9:00-15:30 JST）に取引される銘柄
    "US" … 東京市場の引け後に取引を終える銘柄（米国株・CME先物）。
           日付Dのセッションは日本時間 D+1 の早朝に終わるため、
           日本の営業日Tには「T より前の直近セッション」を対応させる。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    ticker: str  # Yahoo Finance のティッカー
    key: str  # 分析内部で使う短いキー（グラフのラベルにも使う）
    name_ja: str
    market: str  # "JP" or "US"
    group: str


INSTRUMENTS: list[Instrument] = [
    # --- 指数 ---
    Instrument("^N225", "N225", "日経平均株価", "JP", "index"),
    Instrument("^DJI", "DJI", "NYダウ平均", "US", "index"),
    Instrument("^SOX", "SOX", "フィラデルフィア半導体株指数(SOX)", "US", "index"),
    # --- 日経先物（CME。日本時間の夜間〜早朝も取引されるので「時間外」の指標になる）---
    Instrument("NIY=F", "NK_FUT_CME", "日経225先物(CME・円建て)", "US", "futures"),
    # --- 日本の半導体株 ---
    Instrument("8035.T", "TEL", "東京エレクトロン", "JP", "semi_jp"),
    Instrument("6857.T", "ADVANTEST", "アドバンテスト", "JP", "semi_jp"),
    Instrument("6920.T", "LASERTEC", "レーザーテック", "JP", "semi_jp"),
    Instrument("7735.T", "SCREEN", "SCREENホールディングス", "JP", "semi_jp"),
    Instrument("6146.T", "DISCO", "ディスコ", "JP", "semi_jp"),
    Instrument("6723.T", "RENESAS", "ルネサスエレクトロニクス", "JP", "semi_jp"),
    # --- 米国の半導体株 ---
    Instrument("NVDA", "NVDA", "エヌビディア", "US", "semi_us"),
    Instrument("AMD", "AMD", "AMD", "US", "semi_us"),
    Instrument("AVGO", "AVGO", "ブロードコム", "US", "semi_us"),
    Instrument("TSM", "TSM", "TSMC(ADR)", "US", "semi_us"),
    Instrument("MU", "MU", "マイクロン", "US", "semi_us"),
    # --- 参考: 為替（日本株への影響が大きいため参考として収録）---
    Instrument("JPY=X", "USDJPY", "ドル円", "US", "fx"),
]

BASE_KEY = "N225"


def by_key() -> dict[str, Instrument]:
    return {i.key: i for i in INSTRUMENTS}


def by_ticker() -> dict[str, Instrument]:
    return {i.ticker: i for i in INSTRUMENTS}
