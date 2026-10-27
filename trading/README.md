# 5万円運用の記録

Webページ（資金の推移とベンチマーク比較）: https://claude.ai/artifact/71Kr4njy3S9ADqxAW6wBEh

SBI証券（特定口座）で 5万円を1か月運用し、その判断と結果を検証できる形で記録します。発注は Fe さんが手動で行い、Claude が判断・指示・記録を担当します。

| ファイル | 内容 |
|---|---|
| `plan.md` | 運用方針・配分・売買ルール・リスク・ルール変更の記録 |
| `journal.md` | 判断の理由と予想（結果が出る前に書く。追記のみ） |
| `trades.csv` | 約定履歴（記録の正本） |
| `config.json` | 期間・ルールの数値・ベンチマーク定義（ルーティンが読む） |
| `ledger.py` | 保有・現金・評価額・ベンチマーク比較・ルール判定を計算する |

保有・現金・評価額は `trades.csv` から毎回計算します。手で書き換える必要はありません。

## 約定の報告のしかた
「1475 を 53口、424円で買った」のように、Claude に伝えてください。日時、手数料、源泉徴収された税額が分かれば一緒に伝えてください。Claude が `trades.csv` に1行追加し、`journal.md` を更新して、Webページのデータを作り直します。

## コマンド
```bash
python trading/ledger.py status            # 現在の保有・評価額
python trading/ledger.py alerts            # 売買ルールの条件に達していないか（action があると終了コード1）
python trading/ledger.py export out.json   # Webページ用データ
python trading/build_page.py out.html      # Webページ（Artifact）のHTMLを作る
```

## ベンチマーク
運用開始日（2026-10-13）の始値で、5万円で買えるだけ 1321（NEXT FUNDS 日経225連動型上場投信）を1口単位で買い、最終日まで持った場合と比べます。比較は、税引前と「その日に全部売った場合の税引後」の両方で行います。
