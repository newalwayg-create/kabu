"""エントリー・イグジットのシミュレーション（1事例ずつ, 日足のみ）.

- エントリー: "引け"=シグナル日 t の終値 / "寄付"=t+1 の始値
- 固定日数: t+H の終値で決済
- MA到達: 前日終値時点の MA 値（当日の寄付前に既知）を目標に、寄付で上回れば寄付、日中に高値が届けば目標値で決済。
  上限40営業日（到達しなければ t+40 の終値）
- 利確/損切: 当日寄付がどちらかを越えていれば寄付で決済。日中に両方に届いた日は損切りを優先（保守的）。
  上限20営業日（届かなければ t+20 の終値）
"""
from __future__ import annotations

import numpy as np


def simulate(a: dict, i: int, entry: str, rule: tuple):
    """a: 銘柄の配列 dict(open, high, low, close, ma25, ma50, ma75)、i: シグナル日の位置.
    返り値: (リターン, 保有日数, 保有中の最大下落) / 計算不能なら None
    """
    O, Hh, L, C = a["open"], a["high"], a["low"], a["close"]
    n = len(C)
    if entry == "引け":
        px, first = C[i], i + 1
    else:
        if i + 1 >= n:
            return None
        px, first = O[i + 1], i + 1
    kind = rule[0]
    if kind == "固定":
        H = rule[1]
        j = i + H
        if j >= n:
            return None
        lo = L[first:j + 1].min()
        return C[j] / px - 1, j - i, lo / px - 1
    if kind == "MA":
        key, cap = rule[1], 40
        if not (a[key][i] > C[i]):
            return None
        last = min(i + cap, n - 1)
        if i + cap >= n:
            return None
        lo = np.inf
        for j in range(first, last + 1):
            tgt = a[key][j - 1]
            if not (entry == "寄付" and j == first) and O[j] >= tgt:
                lo = min(lo, O[j]); return O[j] / px - 1, j - i, lo / px - 1
            lo = min(lo, L[j])
            if Hh[j] >= tgt:
                return tgt / px - 1, j - i, lo / px - 1
        return C[last] / px - 1, last - i, lo / px - 1
    if kind == "TPSL":
        tp, sl, cap = rule[1], rule[2], 20
        if i + cap >= n:
            return None
        up, dn = px * (1 + tp), px * (1 - sl)
        lo = np.inf
        for j in range(first, i + cap + 1):
            if not (entry == "寄付" and j == first):
                if O[j] <= dn:
                    return O[j] / px - 1, j - i, min(lo, L[j]) / px - 1
                if O[j] >= up:
                    return O[j] / px - 1, j - i, min(lo, O[j]) / px - 1
            lo = min(lo, L[j])
            if L[j] <= dn:
                return -sl, j - i, lo / px - 1
            if Hh[j] >= up:
                return tp, j - i, lo / px - 1
        return C[i + cap] / px - 1, cap, lo / px - 1
    raise ValueError(rule)


RULES = [("固定", 5), ("固定", 10), ("固定", 20), ("MA", "ma25"), ("MA", "ma50"), ("MA", "ma75")] + \
        [("TPSL", tp, sl) for tp in (0.03, 0.05, 0.08) for sl in (0.03, 0.05, 0.08)]


def rule_name(r):
    if r[0] == "固定":
        return f"固定{r[1]}日"
    if r[0] == "MA":
        return f"{r[1][2:]}日線到達(上限40日)"
    return f"利確+{int(r[1]*100)}%/損切−{int(r[2]*100)}%(上限20日)"
