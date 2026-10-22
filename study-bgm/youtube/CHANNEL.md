# チャンネルの周辺設定

素材の生成: `make_branding.py`（`branding/` と `preview_branding.png` を出力）
名前を変えて作り直す: `python3 make_branding.py --name "Quiet Fathoms" --mono "Q."`

---

## 1. チャンネル名

### 推奨: **Halcyon Rooms**（ハンドル `@halcyonrooms`）
- **意味**: halcyon は「穏やかな、平和な」。語源は、冬至のころ海を凪がせて巣を作るとされた伝説の鳥（カワセミ）。海から始まるチャンネルの由来として語れる。
- **Rooms**: 動画 1 本を「1 つの部屋（場所）」と見立てる。Ocean.／Forest.／Rain.／Night. とシリーズを横に広げても名前が合う。
- **読み方**: ハルシオン・ルームズ（HAL-see-on）。英語ネイティブ以外には少し難しい単語なので、覚えてもらう手がかりはプロフィール画像の「点」に持たせる。

### 確認結果（2026-10-22 時点、YouTube 上の同名チャンネルとハンドル）
| 名前 | 結果 | 判断 |
|---|---|---|
| **Halcyon Rooms** | 同名チャンネルなし、`@halcyonrooms` も未使用 | **推奨** |
| Quiet Fathoms | 同名チャンネルなし、ハンドル未使用 | 海専門のチャンネルにするなら第一候補（Fathom は海の深さの単位） |
| Soft Depths | ハンドル未使用だが「Soft Depth」が存在 | 紛らわしいので見送り |
| Undertow Ambient | ハンドル未使用 | 「引き波」で少し不穏な語感なので見送り |
| Quiet Atlas / Still Atlas / Hush Atlas / Drift Atlas / Calm Atlas / Nocturne Atlas / Stillwater Atlas | すべて同名チャンネルあり | 「〜Atlas」は量産系アンビエントで飽和している |
| Lowtide / Stillroom / Driftroom / Aftercalm / Slow Places / Quiet Elsewhere / The Quiet Archive / Somewhere Still / Low Hours / Lumen Lull / Elsewhere Rooms / Stillhours / Halcyon Hours / Hushwater / Kehai / Nagi / Nagi Ambient | 同名チャンネルあり | 見送り |
| Nagi Rooms | ハンドル未使用だが「nagi room.」（登録者 696 人）が存在 | 紛らわしいので見送り |

- ハンドルは登録時に初めて確定する。早めに押さえる。
- Instagram／TikTok／X／ドメインでの空き状況は **未確認**。同じ名前で押さえられるか、登録前に確認する。
- チャンネル名の変更は、ブランドの積み上げを失うのでコストが大きい。**最初に決めて動かさない**（A/B テストの対象にしない）。

---

## 2. ビジュアル（`branding/`）

ブランドマークは **「水平線の上の点」**。点は「Ocean.」の句点であり、ひと休み（pause）の印。

| ファイル | 内容 | 判断 |
|---|---|---|
| `avatar_A1_dot_horizon.png` | 点＋水平線＋水面の反射 | **推奨**。24px でも点と水平線が分かる。バナーと同じ絵なので一貫性がある |
| `avatar_A2_monogram.png` | セリフ体「H.」 | 名前が定着してからの候補。最初は名前の頭文字が伝わらない |
| `avatar_A3_dot.png` | 点だけ | いちばんミニマル。小さい表示では A1 より目立つが、情報が少ない |
| `banner.png` | 2560×1440。名前とタグラインを全デバイスの安全領域（1235×338）内に配置 | デスクトップでもスマホでも文字が切れないことを確認済み（4.7MB、上限 6MB 以内） |
| `watermark.png` | 150×150 の透過 PNG。円の中に点と水平線 | 動画右下に出る「チャンネル登録」ボタンの画像 |

- フォントは Caladea（Apache 2.0）と Inter（SIL OFL）。どちらも商用利用可。
- サムネイル（`thumbnails/T1`）とは「暗い青緑・セリフ体・白」で統一してある。

---

## 3. 概要欄（About）

最初の 1〜2 文は検索結果やチャンネルページに表示されやすいので、何のチャンネルかをすぐ言う。

```
Ambient rooms for sleep, study and meditation.

Each video is a quiet place to stay for a while — the deep sea, a night forest,
rain on a window. Slow, wordless music with soft natural sounds, made to fade
into the background so you can rest, focus or simply breathe.

Original compositions. No talking, no sudden changes.

New rooms are added regularly. Stay as long as you like.
```

- 「No sudden changes」は、睡眠向けに突発音を抑えた版を出すまでは外しておく（今の Ocean 30 分版には船やソナーの音がある）。
- 「New rooms every week」のように頻度を約束するのは、投稿の頻度が固まってから（H9）。

**チャンネルキーワード**: `ambient music, sleep music, study music, meditation music, relaxing music, deep sea ambient, underwater ambience, ocean sounds, focus music, calm music`

---

## 4. 初期設定（YouTube Studio → 設定）

| 項目 | 設定 | 理由 |
|---|---|---|
| アップロードのデフォルト → カテゴリ | Music | 音楽として分類・推薦されるように |
| 動画の言語／タイトルと説明の言語 | English | 翻訳タイトルを足すときの基準になる（H8） |
| 視聴者 | **子ども向けではない（No, it's not made for kids）** | 「子ども向け」にすると、コメント・通知・パーソナライズ広告・再生リストへの保存などが制限される。睡眠用 BGM は一般向けとして出す |
| ライセンス | 標準の YouTube ライセンス | |
| 改変・合成コンテンツの開示 | 「いいえ」 | 開示が求められるのは、実在の人・場所・出来事を本物らしく見せる合成。抽象的な CG 背景とオリジナル曲は該当しない想定（ポリシーは変わるので、アップロード時に確認する） |
| コメント | オン（不適切な可能性があるものは保留） | 「どこで聴いているか」のコメントは、このジャンルのコミュニティ形成になる |
| 透かし | `watermark.png`、表示は「動画の最後」または「カスタム開始時間」 | 動画の全体に出すと、睡眠中の画面には少し気になる |

**「No AI」とは書かない**: 曲はプログラムで作曲しているので、誤解を招く表示になりうる。代わりに「Original compositions」と、事実の範囲で書く。

---

## 5. チャンネルページの構成

| セクション | 内容 |
|---|---|
| 未登録の人向けの予告編 | Ocean 30 分版から 60〜90 秒を切り出す（海面 → 潜る瞬間の泡 → 深海）。冒頭 5 秒で「どこへ連れて行くか」を見せる（未作成） |
| 登録者向けのおすすめ | 最新の動画 |
| 再生リスト 1 | **Ocean.**（シリーズ。30 分・1 時間・3 時間版をまとめる） |
| 再生リスト 2 | **Long sessions for sleep**（3 時間以上の版） |
| 再生リスト 3 | **For study & focus**（30 分〜1 時間の版） |

再生リストのタイトルも検索の対象になるので、用途の言葉を入れる。

---

## 6. 動画の説明文テンプレート

```
Ocean. — a 30-minute descent from the surface to the abyss and back.
Deep sea ambient music for sleep, study and meditation.

Chapters
0:00 Surface
2:40 Shallows
6:24 Descent
9:04 Twilight Zone
13:20 The Deep
18:08 The Abyss
22:56 Ascent
26:40 Return to the Surface

Original composition. Pads, fretless bass, vibraphone and choir,
with soft underwater sounds — bubbles, a distant ship, sonar.

#ambient #sleepmusic #studymusic
```

---

## 7. この設定に関する仮説（`experiments.csv` に追記）

| ID | 仮説 | 比べ方 |
|---|---|---|
| H12 | 未登録の人向けの予告編があると、チャンネルページからの登録率が上がる | 予告編の設定前後のチャンネルページ経由の登録率 |
| H13 | 再生リストの名前に用途の言葉を入れると、再生リスト経由の再生が増える | 名前の変更前後 |

プロフィール画像の変更は A/B テストできないので、変える場合は日付と前後の数字を記録しておく（効果の判定はゆるく）。
