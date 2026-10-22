# チャンネルの周辺設定

素材の生成: `make_branding_solid.py`（採用案。`branding_solid/` と `preview_solid.png` を出力）
不採用にした海寄りの案: `make_branding.py`（`branding/` と `preview_branding.png`）

---

## 1. チャンネル名

### 推奨: **Halcyon Rooms**（ハンドル `@halcyonrooms`）
- **意味**: halcyon は「穏やかな、平和な」。語源は、冬至のころ海を凪がせて巣を作るとされた伝説の鳥（カワセミ）。海から始まるチャンネルの由来として語れる。
- **Rooms**: 動画 1 本を「1 つの部屋（場所）」と見立てる。Ocean.／Forest.／Rain.／Night. とシリーズを横に広げても名前が合う。
- **読み方**: ハルシオン・ルームズ（HAL-see-on）。英語ネイティブ以外には少し難しい単語。
- **海に限定されないか**: 語源は海の伝説だが、一般には「halcyon days（穏やかな日々）」のように「穏やかな」の意味で使われる。海のイメージは表に出さず、由来として語れる程度にとどめる。

### 確認結果（2026-10-22 時点、YouTube 上の同名チャンネルとハンドル）
| 名前 | 結果 | 判断 |
|---|---|---|
| **Halcyon Rooms** | 同名チャンネルなし、`@halcyonrooms` も未使用 | **推奨** |
| Quiet Fathoms | 同名チャンネルなし、ハンドル未使用 | 海専門にはしない方針になったので見送り（Fathom は海の深さの単位） |
| Soft Depths | ハンドル未使用だが「Soft Depth」が存在 | 紛らわしいので見送り |
| Undertow Ambient | ハンドル未使用 | 「引き波」で少し不穏な語感なので見送り |
| Quiet Atlas / Still Atlas / Hush Atlas / Drift Atlas / Calm Atlas / Nocturne Atlas / Stillwater Atlas | すべて同名チャンネルあり | 「〜Atlas」は量産系アンビエントで飽和している |
| Lowtide / Stillroom / Driftroom / Aftercalm / Slow Places / Quiet Elsewhere / The Quiet Archive / Somewhere Still / Low Hours / Lumen Lull / Elsewhere Rooms / Stillhours / Halcyon Hours / Hushwater / Kehai / Nagi / Nagi Ambient | 同名チャンネルあり | 見送り |
| Nagi Rooms | ハンドル未使用だが「nagi room.」（登録者 696 人）が存在 | 紛らわしいので見送り |

- ハンドルは登録時に初めて確定する。早めに押さえる。
- Instagram／TikTok／X／ドメインでの空き状況は **未確認**。同じ名前で押さえられるか、登録前に確認する。
- チャンネル名の変更は、ブランドの積み上げを失うのでコストが大きい。**最初に決めて動かさない**（A/B テストの対象にしない）。

---

## 2. ビジュアル

### 方針（2026-10-22 決定）
**チャンネルは特定のテーマを持たない「中立な額縁」にし、毎回のコンセプトはサムネイルに任せる。**
動画ごとにコンセプトを変えるチャンネルなので、チャンネルの見た目は単色でシンプルにする。

### 採用案（`branding_solid/`、`make_branding_solid.py`）
| 項目 | 採用 | 理由 |
|---|---|---|
| アイコン | **sage（くすんだ緑、RGB 138,150,132 / #8A9684）の単色。点なし** → `avatar_sage.png` | 下記の比較の結果。中央の点は小さい表示ではほぼ見えず、なくしても色味があるので読み込み中の丸と見間違えない（2026-10-22 決定） |
| バナー | **なし** | 単色バナーは「空の帯」に見えた。なしの方がすっきりして、動画のサムネイルが主役になる |
| 透かし | `watermark_sage.png`（アイコンと同じ sage の丸、細い白縁つき） | アイコンとそろえる。白縁は明るい映像・暗い映像のどちらでも見えるように |

### 比較して分かったこと（`preview_solid.png`）
| 案 | 結果 |
|---|---|
| アイコンなし | 設定しないと「何もない」ではなく、YouTube 既定の「色付きの丸に頭文字」が出る。作りかけ・量産チャンネルによくある見た目で、静かな方向性と真逆になる → **不採用** |
| グレー（stone / fog） | 両方のモードで見えるが、小さいと YouTube の読み込み中の灰色の丸と区別がつかない → 不採用 |
| 生成り（bone） | ライトモードで背景に沈む → 不採用 |
| 墨（ink） | ダークモードで背景に沈む → 不採用 |
| 少し色味のある中間色（clay / sage） | どちらのモードでも「意図して選んだ色」に見える → **sage を採用**、clay は次点 |
| 中央の点（clay / sage ＋ dot） | 24〜36px ではほぼ見えない。チャンネルページでだけ気づく程度 → 不採用（単色のみ） |
| 単色バナー | 空の帯に見える → 不採用（バナーなしを採用） |

### 不採用にした案（`branding/`、`make_branding.py`）
「水平線の上の点」（暗い青緑の水平線と水面の反射）のアイコン・バナー・透かし。
**不採用の理由**: 海に寄りすぎていて、動画ごとにコンセプトを変えるチャンネルの方針と合わない。
単色案と比べるための記録として、ファイルは残してある。

### 動画をまたいだ統一感の出し方
チャンネルの見た目が中立なので、シリーズとしての統一感は **サムネイルの文字の型** で出す。
- 中央に、セリフ体で 1 単語＋句点（「Ocean.」「Forest.」「Rain.」…）
- その下に、字間を広くとった小さな副題
- 背景だけを毎回のコンセプトに合わせて変える

- フォントは Caladea（Apache 2.0）と Inter（SIL OFL）。どちらも商用利用可。

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
| 透かし | `branding_solid/watermark_sage.png`、表示は「動画の最後」または「カスタム開始時間」 | 動画の全体に出すと、睡眠中の画面には少し気になる |

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
