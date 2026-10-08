"""5万円運用の記録・評価・ルール判定。

  python trading/ledger.py status            # 現在の保有・現金・評価額・ベンチマーク比較
  python trading/ledger.py alerts            # 売買ルールの条件に達していないか判定（ルーティン用）
  python trading/ledger.py export OUT.json   # Webページ用のデータを書き出す

記録の正本は trades.csv（約定履歴）と config.json（ルール）。
保有・現金・評価額はすべてそこから計算するので、手で書き換えない。
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))


def load_config() -> dict:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def load_trades() -> pd.DataFrame:
    df = pd.read_csv(HERE / "trades.csv", dtype={"ticker": str})
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    for c in ["qty", "price", "fee", "tax"]:
        df[c] = pd.to_numeric(df[c]).fillna(0)
    return df.sort_values(["date", "time"], kind="stable").reset_index(drop=True)


@dataclass
class Position:
    ticker: str
    qty: int = 0
    cost: float = 0.0  # 取得総額（移動平均法）
    entry_date: pd.Timestamp | None = None

    @property
    def avg(self) -> float:
        return self.cost / self.qty if self.qty else 0.0


@dataclass
class Book:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized: float = 0.0  # 実現損益（手数料控除後、税引前）
    tax_paid: float = 0.0


def replay(trades: pd.DataFrame, capital: float, until: pd.Timestamp | None = None) -> Book:
    """約定履歴を順に適用して、ある日の終わり時点の保有と現金を返す。"""
    book = Book(cash=capital)
    for t in trades.itertuples():
        if until is not None and t.date > until:
            break
        p = book.positions.setdefault(t.ticker, Position(t.ticker))
        amount = t.qty * t.price
        if t.side == "BUY":
            book.cash -= amount + t.fee
            if p.qty == 0:
                p.entry_date = t.date
            p.cost += amount + t.fee
            p.qty += int(t.qty)
        elif t.side == "SELL":
            if t.qty > p.qty:
                raise ValueError(f"{t.date.date()} {t.ticker}: 保有 {p.qty} より多い {t.qty} を売却しています")
            cost_out = p.avg * t.qty
            book.realized += amount - t.fee - cost_out
            book.cash += amount - t.fee - t.tax
            book.tax_paid += t.tax
            p.cost -= cost_out
            p.qty -= int(t.qty)
            if p.qty == 0:
                p.cost = 0.0
                p.entry_date = None
        else:
            raise ValueError(f"side は BUY か SELL: {t.side}")
    return book


def fetch_daily(tickers: list[str], start: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(tickers, start=start, auto_adjust=False, progress=False, group_by="ticker")
    out = {}
    for t in tickers:
        if t in raw.columns.get_level_values(0):
            out[(t, "Open")] = raw[t]["Open"]
            out[(t, "Close")] = raw[t]["Close"]
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.dropna(how="all")
    for t in tickers:
        if (t, "Close") in df:
            _fix_splits(df, t)
    return df


def _fix_splits(df: pd.DataFrame, t: str) -> None:
    """Yahoo の ETF は分割前の価格が未調整のことがあるので、最新の単位にそろえる。

    前日比が 0.55 倍未満または 1.8 倍超の日を分割とみなす（ETFの1日の値動きでは起きない幅）。
    期間中に保有銘柄が分割された場合、口数の調整は trades.csv に記録する必要がある。
    """
    c = df[(t, "Close")]
    r = c / c.ffill().shift(1)
    for d in r[(r < 0.55) | (r > 1.8)].index:
        k = round(1 / r[d]) if r[d] < 1 else 1 / round(r[d])
        before = df.index < d
        df.loc[before, (t, "Close")] /= k
        df.loc[before, (t, "Open")] /= k
        # 分割日の始値が未調整のまま残っている場合も直す
        if df.loc[d, (t, "Open")] / df.loc[d, (t, "Close")] > 1.8:
            df.loc[d, (t, "Open")] /= k


def fetch_last(tickers: list[str]) -> dict[str, tuple[float, str]]:
    """直近の約定値（5分足の最終値。Yahooは東証で約20分遅れ）。"""
    import yfinance as yf

    out = {}
    raw = yf.download(tickers, period="5d", interval="5m", auto_adjust=False, progress=False, group_by="ticker")
    for t in tickers:
        try:
            s = raw[t]["Close"].dropna()
            out[t] = (float(s.iloc[-1]), s.index[-1].tz_convert(JST).strftime("%Y-%m-%d %H:%M"))
        except (KeyError, IndexError):
            pass
    return out


def tax_on(gain: float, rate: float) -> float:
    return max(gain, 0.0) * rate


def nav_series(cfg: dict, trades: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """日次の評価額（運用 vs ベンチマーク）。税引後は「その日に全部売ったら」の値。"""
    start = pd.Timestamp(cfg["start_date"])
    end = pd.Timestamp(cfg["end_date"])
    bt = cfg["benchmark"]["ticker"]
    days = prices.index[(prices.index >= start) & (prices.index <= end)]
    rate = cfg["tax_rate"]
    cap = cfg["capital"]
    rows = []
    b_open = prices[(bt, "Open")].get(start) if len(days) and days[0] == start else None
    if b_open is None and len(days):
        b_open = prices[(bt, "Open")].loc[days[0]]
    b_qty = math.floor(cap / b_open) if b_open else 0
    b_cash = cap - b_qty * b_open if b_open else cap
    for d in days:
        book = replay(trades, cap, d) if not trades.empty else Book(cash=cap)
        mv, unreal = 0.0, 0.0
        for p in book.positions.values():
            if p.qty:
                px = prices[(p.ticker, "Close")].loc[:d].dropna().iloc[-1]
                mv += p.qty * px
                unreal += p.qty * px - p.cost
        nav = book.cash + mv
        gain_total = book.realized + unreal
        after_tax = nav + book.tax_paid - tax_on(gain_total, rate)
        b_px = prices[(bt, "Close")].loc[d]
        b_nav = b_cash + b_qty * b_px
        b_after = b_nav - tax_on(b_qty * (b_px - b_open), rate)
        rows.append({"date": d, "nav": nav, "nav_after_tax": after_tax, "cash": book.cash,
                     "bench_nav": b_nav, "bench_after_tax": b_after})
    df = pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()
    df.attrs["bench"] = {"qty": b_qty, "entry": b_open, "cash": b_cash}
    return df


def stop_levels(cfg: dict, pos: Position, high_since_entry: float | None) -> dict:
    rule = cfg["positions"].get(pos.ticker)
    if not rule or not pos.qty:
        return {}
    avg = pos.avg
    stop = avg * (1 + rule["stop_pct"])
    trigger = avg * (1 + rule["trail_trigger_pct"])
    locked = high_since_entry is not None and high_since_entry >= trigger
    if locked:
        stop = avg * (1 + rule["trail_lock_pct"])
    return {"avg": avg, "stop": stop, "trigger": trigger, "locked": locked}


def alerts(now: datetime | None = None) -> list[dict]:
    cfg = load_config()
    trades = load_trades()
    book = replay(trades, cfg["capital"]) if not trades.empty else Book(cash=cfg["capital"])
    now = now or datetime.now(JST)
    held = [p for p in book.positions.values() if p.qty]
    tickers = sorted(set([p.ticker for p in held] + list(cfg["positions"])))
    last = fetch_last(tickers)
    out = []

    start = date.fromisoformat(cfg["start_date"])
    end = date.fromisoformat(cfg["end_date"])
    if not held and trades.empty and now.date() >= start:
        out.append({"level": "action", "msg": "初回の買い注文がまだ記録されていません。plan.md の『初回注文』を実行し、約定を報告してください。"})

    nav = book.cash
    for p in held:
        if p.ticker not in last:
            out.append({"level": "warn", "msg": f"{p.ticker} の株価を取得できませんでした。"})
            continue
        px, ts = last[p.ticker]
        nav += p.qty * px
        daily = fetch_daily([p.ticker], str(p.entry_date.date()))
        hi = float(daily[(p.ticker, "Close")].max())  # 利益確保の判定は終値で行う（plan.md）
        lv = stop_levels(cfg, p, hi)
        name = cfg["positions"].get(p.ticker, {}).get("name", p.ticker)
        if lv and px <= lv["stop"]:
            out.append({"level": "action", "msg": f"【損切り/利益確保ライン到達】{name}({p.ticker}) 現在値 {px:,.1f}円（{ts}）≦ ライン {lv['stop']:,.1f}円。"
                        f"SBIの逆指値が約定しているはずです。約定を確認し、未約定なら {p.qty} 口を成行で売ってください。"})
        elif lv and lv["locked"] and px > lv["stop"]:
            out.append({"level": "info", "msg": f"{name}: 含み益が+{cfg['positions'][p.ticker]['trail_trigger_pct']*100:.0f}%に達したことがあります。"
                        f"逆指値を {lv['stop']:,.0f}円 以上に引き上げてあるか確認してください（取得単価 {lv['avg']:,.1f}円）。"})
    if held and nav <= cfg["portfolio_stop"]["nav_below"]:
        out.append({"level": "action", "msg": f"【全体の損切り】評価額 {nav:,.0f}円 が {cfg['portfolio_stop']['nav_below']:,}円 以下です。全銘柄を売却してください。"})
    if held and now.date() >= end:
        out.append({"level": "action", "msg": f"運用期間の最終日（{end}）です。全銘柄を引け成行で売却し、約定を報告してください。"})
    elif held and (end - now.date()).days <= 3:
        out.append({"level": "info", "msg": f"運用終了日 {end} まであと {(end - now.date()).days} 日です。"})
    return out


def status() -> str:
    cfg = load_config()
    trades = load_trades()
    book = replay(trades, cfg["capital"]) if not trades.empty else Book(cash=cfg["capital"])
    lines = [f"現金 {book.cash:,.0f}円 / 実現損益 {book.realized:,.0f}円 / 源泉徴収済み {book.tax_paid:,.0f}円"]
    held = [p for p in book.positions.values() if p.qty]
    last = fetch_last([p.ticker for p in held]) if held else {}
    nav = book.cash
    for p in held:
        px = last.get(p.ticker, (float("nan"), ""))[0]
        nav += p.qty * px
        lines.append(f"  {p.ticker} {p.qty}口 取得単価 {p.avg:,.1f} 現在 {px:,.1f} 評価損益 {p.qty * px - p.cost:+,.0f}円")
    lines.append(f"評価額 {nav:,.0f}円（元本比 {nav / cfg['capital'] * 100 - 100:+.2f}%）")
    return "\n".join(lines)


def export(path: str) -> None:
    cfg = load_config()
    trades = load_trades()
    tickers = sorted(set(list(cfg["positions"]) + [cfg["benchmark"]["ticker"]] + (list(trades["ticker"].unique()) if not trades.empty else [])))
    prices = fetch_daily(tickers, (pd.Timestamp(cfg["start_date"]) - pd.Timedelta(days=40)).strftime("%Y-%m-%d"))
    nav = nav_series(cfg, trades, prices)
    book = replay(trades, cfg["capital"]) if not trades.empty else Book(cash=cfg["capital"])
    holdings = []
    for p in book.positions.values():
        if not p.qty:
            continue
        px = float(prices[(p.ticker, "Close")].dropna().iloc[-1])
        hi = float(prices[(p.ticker, "Close")].loc[p.entry_date:].max())
        lv = stop_levels(cfg, p, hi)
        holdings.append({"ticker": p.ticker, "name": cfg["positions"].get(p.ticker, {}).get("name", p.ticker), "qty": p.qty,
                         "avg": round(p.avg, 2), "last": px, "pnl": round(p.qty * px - p.cost),
                         "stop": round(lv.get("stop", 0), 1), "trigger": round(lv.get("trigger", 0), 1), "locked": lv.get("locked", False)})
    # 参考: 開始前の値動き（計画時点の価格からの推移）
    pre = {t: [[d.strftime("%Y-%m-%d"), float(v)] for d, v in prices[(t, "Close")].dropna().tail(30).items()] for t in tickers}
    data = {
        "generated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "config": cfg,
        "trades": [] if trades.empty else [
            {**{k: (v.strftime("%Y-%m-%d") if isinstance(v, pd.Timestamp) else v) for k, v in r.items()}} for r in trades.fillna("").to_dict("records")],
        "cash": round(book.cash), "realized": round(book.realized), "tax_paid": round(book.tax_paid),
        "holdings": holdings,
        "nav": [] if nav.empty else [{"date": d.strftime("%Y-%m-%d"), **{k: round(float(v)) for k, v in r.items()}} for d, r in nav.iterrows()],
        "bench": {k: (round(float(v), 2) if v is not None else None) for k, v in nav.attrs.get("bench", {}).items()},
        "recent": pre,
        "journal": (HERE / "journal.md").read_text(encoding="utf-8"),
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(status())
    elif cmd == "alerts":
        res = alerts()
        print(json.dumps(res, ensure_ascii=False, indent=1) if res else "[] 条件に達したルールはありません")
        sys.exit(1 if any(a["level"] == "action" for a in res) else 0)
    elif cmd == "export":
        export(sys.argv[2])
    else:
        print(__doc__)
