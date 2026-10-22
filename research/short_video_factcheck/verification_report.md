# ショート動画市場リサーチ ファクトチェック報告

検証日：2026-10-22
対象：別AIがまとめた「ショート動画（Instagramリール・YouTubeショート・TikTok）の視聴需要と市場」に関する主張 18件（A1〜D3）

---

## 判定サマリー

| 判定 | 件数 | 該当ID |
|---|---|---|
| 確認済み | 10 | A1, A3, A4, A7, B1, C1, C2, C3, C5, D2 |
| 一部相違 | 4 | A2, A5, A6, B3 |
| 一次情報見つからず | 4 | B2, C4, D1, D3 |
| 反証あり | 0 | — |
| 合計 | 18 | |

### 判定の補足（要注意の5件）
- **A2**：66%／64%／45%は Clutch の記事で確認できた。**23%は Clutch の資料に見当たらない。**
- **A5**：57.4%は一次リリースと一致した。ただし「ビジネス・ニュースの情報収集に活用」しているのは視聴者の一部（時事ニュース72名／ビジネス40名、母数266名）で、主張の書き方は拡大解釈になっている。
- **B3**：13%は Syracuse 大学の公式リリースと一致した。しかし共同調査者 Ipsos の公式ページでは **25%** と報告されており、**一次情報どうしで数字が食い違う**。
- **C4**：「Social Media Today」発とされているが、同誌の記事に該当する数字はない。数字の出どころはマーケ会社のブログで、裏付けデータは見つからなかった。
- **A6**：主張の URL は 2026年の論文（Zhang ほか）で、「Chen et al., 2024」はその論文の中で引用されている文献にすぎない。しかも Chen ほか（2024）が扱っているのは「問題的な利用」についてのメタ分析。

> 依頼に記載された出典以外の独立資料（公的統計、他社調査、他の論文、プラットフォームの発表）による照合は `cross_check_additional_sources.md` にまとめた。その照合で判定が変わった主張はない。

---

## 作業上の解釈・制約（必読）

1. **ページの直接取得はすべてできなかった。** この作業環境のネットワーク方針（送信プロキシ）により、WebFetch／curl での外部ページ取得がすべて拒否された。拒否されたホストの例：commercepick.com、clutch.co、ecnomikata.com、prtimes.jp、comnico.jp、google.com。ルールに従い回避策は取っていない。
   - 代わりに **Web検索ツールの検索結果（検索エンジン側が取得したページの抜粋・要約）** で検証した。本レポートの「一次情報での数字」は、検索結果に表示された一次ページの抜粋に基づく。
   - 依頼文に挙げられた出典URL（二次まとめ記事）も同じ理由で直接開けていない。各主張の「依頼記載URL」欄に、アクセス状況を記録した。
   - **最終判断の前に、一次URLを人が直接開いて数字を照合することを推奨する。** 特に検索結果どうしで食い違いが出た B3（13%／25%）と A2（n=438／483）。
2. **判定の基準**
   - 確認済み：一次情報（調査主体の公式リリース、論文、プラットフォーム公式ページ・公式ブログ）で、数字・事実が主張と一致する。
   - 一部相違：一次情報は存在するが、数字の一部、出典の表示、意味の範囲のいずれかが主張と食い違う。
   - 一次情報見つからず：二次記事以外に根拠が見つからない。または根拠が推計・宣伝記事しかない。
   - 反証あり：一次情報が主張と明確に矛盾する。
3. **D2** は単独の主張ではなく、「複数推計の比較と差の理由の説明」という依頼として扱った。判定は「推計にばらつきがある」という事実についてのもの。
4. 調査主体の「利害関係」は、検索で確認できた事業内容に基づいて書いた。確認できなかったものは「未確認」とした。

---

## A. 視聴需要

### A1. 視聴目的「暇つぶし」80.2%、「暇つぶし」のみ選択 44.1%（コムニコ、600人）
1. **判定**：確認済み
2. **一次情報**
   - コムニコ公式ニュース「ショート動画視聴後に『商品・サービス購入のための行動を取った』4割、広告動画とわかっていても『内容が面白ければ最後まで見る』約3割」 https://www.comnico.jp/news/shortmovie_20251216
   - 同 PR TIMES版 https://prtimes.jp/main/html/rd/p/000000267.000028382.html
   - レポート版 https://www.comnico.jp/we-love-social/short-report
   - 依頼記載URL（commercepick.com）：二次記事。アクセス不可（環境のネットワーク制限）。
3. **調査時期・公開日**：実査 2025年10月28日〜29日／公開 2025年12月16日。約1年前のデータ。
4. **サンプル・方法**：Instagram・TikTok・YouTube の利用者 600名。インターネット調査。年齢は「10代〜60代」と書く記事と、レポート版の「全国18〜69歳」とで表記が異なる。
5. **調査主体・利害関係**：株式会社コムニコ。SNSマーケティング支援会社で、「ショート動画制作プラン」を販売している（PR TIMES 000000182.000028382）。自社サービスに関係する領域の自社調査。
6. **一次情報での表現**：視聴目的「暇つぶし」80.2%、「暇つぶし」のみを選択 44.1%。そのほか「流行情報の収集」「商品・サービスの情報収集」「趣味・学習」が同程度だった。
7. **注意点**
   - 母集団は3プラットフォームのいずれかを使っている人に限られ、ネット調査パネルである。
   - 年齢下限の表記が資料によって違う（10代か18歳か）。
   - 複数回答の設問。

### A2. 楽しむ理由：すぐ見られる 66%、面白い 64%、学べる 45%、新商品・トレンドを知れる 23%（Clutch）
1. **判定**：一部相違（66／64／45%は確認できた。23%は一次情報に見当たらない）
2. **一次情報**
   - Clutch「What Makes Short-Form Video Content So Addictive」 https://clutch.co/resources/short-form-video-content （依頼記載URLと同じ。直接アクセスは不可）
   - 関連リリース：Business Wire「Clutch Report: 95% of Consumers Watch Short-Form Videos Regularly…」（2025年11月12日） https://www.businesswire.com/news/home/20251112921539/en/
3. **調査時期・公開日**：調査 2025年10月（関連記事による）。記事の日付は2025年12月11日。
4. **サンプル・方法**：記事本文は「438 consumers」。一方、他の Clutch ページは「483 consumers（米国、2025年10月）」と書いている。どちらが正しいか、また同じ調査なのかは確認できなかった。方法論の詳細（パネル、回答者の選び方）は検索結果では見えなかった。
5. **調査主体・利害関係**：Clutch。B2Bのサービス提供会社（制作会社・マーケ会社）のレビュー・マッチングプラットフォームで、掲載企業への送客がビジネス。動画制作の需要が大きいと示すことに利害がある。
6. **一次情報での表現**
   - 66%：quick and easy to watch
   - 64%：entertaining and humorous
   - 45%：teaches them something new
   - 23%：Clutch の資料では見つからなかった。検索で出てきた「23%」は HubSpot の「ショート動画で商品を知ることへの選好が前年比+23%（2023年）」という別調査・別指標で、取り違えの可能性がある（断定はできない）。
7. **注意点**
   - サンプル数の表記が438と483で一致しない。
   - 同じ64%が、別の Clutch リリースでは「ブランドをフォローする動機」として使われている。
   - 米国の消費者が対象で、日本にそのまま当てはめられるかは不明。
   - Media.net の別調査（72%／58%）と混同しやすい。

### A3. Z世代が最後まで見る動画1位「面白い・笑える」62.5%（LIH、64人、男性85.9%）
1. **判定**：確認済み（数字は一致。ただし調査の質には大きな制約がある）
2. **一次情報**
   - PR TIMES「【Z世代のリアル調査】企業のショート動画、46.9％が『即スキップ』も“面白さ”があれば最後まで」 https://prtimes.jp/main/html/rd/p/000000004.000177134.html
   - 依頼記載URL（commercepick.com）：二次記事。アクセス不可。
3. **調査時期・公開日**：調査 2026年6月20日〜7月25日。2026年夏の公開。新しいデータ。
4. **サンプル・方法**：10〜20代を中心とした男女64名。Googleフォームによるネットアンケート。有効回答は64件で、内訳は男性85.9%・女性10.9%・無回答3.1%。
5. **調査主体・利害関係**：株式会社LIH。事業内容は検索で確認できず「未確認」。リリースは企業のショート動画活用を促す内容。
6. **一次情報での表現**：企業のショート動画で最後まで見てしまうもの（複数回答）は、1位「面白い・笑える」62.5%。続いて「好きなアーティストや人物が出ている」45.3%、「役に立つ情報がある」39.1%、「裏側やリアルな雰囲気が見える」34.4%。
7. **注意点**
   - n=64と非常に少なく、男性が85.9%と大きく偏っている。
   - Googleフォームで集めた便宜的なサンプルで、無作為抽出ではない。「Z世代」全体の傾向とは言えない。
   - 「男性85.9%」は回答者の構成で、調査結果の数字ではない。

### A4. 10代の7割超がほぼ毎日視聴、1日1時間以上は10代で4割弱（LINEリサーチ）
1. **判定**：確認済み
2. **一次情報**
   - PR TIMES「【LINEリサーチ】ショート動画を『ほぼ毎日見ている』割合は、若い年代ほど高い傾向」 https://prtimes.jp/main/html/rd/p/000000415.000129774.html
   - LINEリサーチ公式note https://note.com/linesurveys_jp/n/ndf8f70b23d35
   - 依頼記載URL（ecnomikata.com）：二次記事。アクセス不可。
3. **調査時期・公開日**：実査 2024年3月4日〜6日／公開 2024年4月。**約2年半前のデータ**で、検証日時点では古い部類に入る。
4. **サンプル・方法**：日本全国の15〜64歳のLINEユーザー男女。スマートフォンWeb調査。有効回収 5,257サンプル。
5. **調査主体・利害関係**：LINEリサーチ（LINEヤフー株式会社）。自社のリサーチパネルを使った調査サービス。LINEヤフーは自社でも動画サービスを運営しているが、この調査との直接の利害は特定できない。
6. **一次情報での表現**
   - 「ほぼ毎日見ている」：10代で7割超、20代で約6割、30〜60代で3〜4割台。
   - 「1日に1時間以上」：10代で4割弱が最も高く、40〜60代では1割未満。
7. **注意点**
   - 「ほぼ毎日」は「1時間以上」「30分以上〜1時間未満」「30分未満」の合計と定義されており、短時間の視聴も含む。
   - 「ショート動画」は「1分程度の縦型動画」と定義（YouTubeショート・TikTokなど）。
   - 10代は15〜19歳だけ。対象はLINEユーザーに限られる。
   - 一次情報の表記は概数（「7割超」「4割弱」）で、正確な%は検索結果では確認できなかった。

### A5. 管理職層の57.4%がショート動画を視聴し、ビジネス・ニュースの情報収集に活用（ベクトル、300人）
1. **判定**：一部相違（57.4%は一致。「活用」の範囲が拡大解釈）
2. **一次情報**
   - PR TIMES「『ベクトルショート動画ラボ』を設立、初の意識調査を実施 企業の管理職層の約6割がショート動画を視聴し、ビジネス分野や最新ニュースの情報取得に活用していることが判明」 https://prtimes.jp/main/html/rd/p/000000416.000000204.html （依頼記載URLと同じ。直接アクセスは不可）
   - 同内容の適時開示PDF（2026年2月5日） https://www.nikkei.com/markets/ir/irftp/data/tdnr/tdnetg3/20260205/frh9at/140120260204547477.pdf
3. **調査時期・公開日**：実査 2025年12月／公開 2026年2月5日。
4. **サンプル・方法**：全国20〜69歳の管理職層（部長クラス、経営層、代表取締役）300名。インターネット調査で、実査は楽天インサイト。
5. **調査主体・利害関係**：株式会社ベクトル。PR会社で、調査はショート動画事業の研究組織「ベクトルショート動画ラボ」設立の告知と同時に発表された。自社サービスの宣伝を兼ねた調査。
6. **一次情報での表現**
   - 視聴：「よく見る」23.7%と「ときどき見る」33.7%の合計で57.4%。最も多いプラットフォームはYouTubeショート。
   - 視聴ジャンル（有効回答266名）：時事ニュース72名、ビジネス40名、キャリア23名。
   - 「最新ニュースの取得」148名は、**SNS全般の利用目的**についての設問の結果。
   - 視聴後に購入・利用などの行動をとった経験：27.4%。
7. **注意点**
   - 主張の書き方では57.4%全員がビジネス・ニュースに活用しているように読めるが、ショート動画でビジネス分野を見ているのは266名中40名（約15%）、時事ニュースは72名（約27%）にとどまる。
   - 見出しの「約3人に1人が購入行動」と本文の27.4%の関係は、検索結果では整合を確認できなかった。
   - 同じ時期に同社が出した「40〜60代287名」調査とは別の調査なので、混同しないこと。

### A6. 逃避・ストレス解消の動機がショート動画利用と正の関連（Chen et al., 2024）
1. **判定**：一部相違（主張の中身は文献上で支持される。ただし出典の示し方と、扱っている概念の範囲が食い違う）
2. **一次情報**
   - 依頼記載URL：Zhang, Ren, Wu, Shi, Liu「How do core personality traits influence short video dependence among Chinese college students?…」Frontiers in Psychology（2026年2月25日、DOI 10.3389/fpsyg.2026.1763608） https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2026.1763608/full （PubMed 41822439）
   - 引用されている元文献：Chen, Zhang, Zhong, Zhao (2024)「Motivations behind problematic short video use: A three-level meta-analysis」Telematics and Informatics 95, 102196（DOI 10.1016/j.tele.2024.102196）。本文には直接アクセスできず、引用している側の記述でのみ確認した。
3. **調査時期・公開日**：Chen ほか 2024年／Zhang ほか 2026年2月。
4. **サンプル・方法**
   - Chen ほか：33研究を統合した3レベルのメタ分析。
   - Zhang ほか：中国の大学生825名への横断的な質問紙調査（I-PACEモデルによる直列媒介分析）。
5. **調査主体・利害関係**：大学の研究者による査読論文。商業的な利害は確認されていない。
6. **一次情報での表現**
   - Zhang ほか：「users engage with short-video for specific motivations, such as escapism and stress relief」と書き、Chen et al., 2024 を引用。
   - Chen ほか（引用元の要約による）：逃避（escapism）が**短尺動画依存・問題的利用**と最も強く関連し、次いで自己補償、ストレス解消。
7. **注意点**
   - 依頼記載URLは Chen ほかの論文ではなく、それを引用している別の論文。
   - Chen ほかの対象は「利用」一般ではなく「問題的利用（problematic use）／依存」。「利用と正の関連」という主張は概念を広げている。
   - 効果量は確認できていない。元になった研究の多くは中国の若年層を対象にした横断研究で、因果関係は言えない。

### A7. ショート動画視聴は浅い学習アプローチへの選好を予測する
1. **判定**：確認済み
2. **一次情報**：Thorsten Otto「Should educators be concerned? The impact of short videos on rational thinking and learning: A comparative analysis」Computers & Education 234（2025）105330、DOI 10.1016/j.compedu.2025.105330 https://www.sciencedirect.com/science/article/pii/S0360131525000983 （依頼記載URLと同じ。直接アクセスは不可）
3. **調査時期・公開日**：2025年（第234巻、2025年9月号）。
4. **サンプル・方法**
   - 研究1：質問紙調査 n=169（ショート動画利用、合理的思考、学業上の満足遅延、表層的学習）。
   - 研究2：オンライン実験 n=123（2×2の被験者間計画。ショート動画視聴の有無 × 教材形式〔動画／テキスト〕）。
5. **調査主体・利害関係**：単著の学術論文（査読誌）。商業的な利害は確認されていない。
6. **一次情報での表現**：ハイライトに「short video use is positively associated with a surface learning approach」「watching short videos predicts a preference for a surface learning approach」とある。合理的思考とは負の関連。ショート動画形式の教材では知識獲得の成績が低かった。
7. **注意点**
   - 研究1は横断調査で、そこでの「predict」は統計的な予測の意味。研究2の実験で示されたのは、その場の（状況的な）表層的学習が高まったという短期の効果。
   - サンプルは小さい。参加者の国や所属は確認できなかった。
   - 別の検索結果に異なるDOI（10.1007/s10956-018-9736-2）を付けた参照があったが、ScienceDirect・ACM DL上のDOIは 10.1016/j.compedu.2025.105330。

---

## B. AIコンテンツへの受け止め

### B1. 新規YouTubeユーザーに表示される動画の20%超が「AIスロップ」（Kapwing調査）
1. **判定**：確認済み（数字は一致。測定範囲がごく限られる点に強い注意）
2. **一次情報**
   - Kapwing「AI Slop Report: The Global Rise of Low-Quality AI Videos」 https://www.kapwing.com/blog/ai-slop-report-the-global-rise-of-low-quality-ai-videos/
   - 制作協力 NeoMam Studios の事例ページ https://neomam.com/projects/youtube-ai-slop-report/
   - 依頼記載URL（primetimer.com）：二次記事。アクセス不可で、検索でも該当記事は特定できなかった。
3. **調査時期・公開日**：調査は2025年11月（NeoMamとの共同とする投稿による）。報道は2025年12月〜2026年1月（BetaNews 2025年12月3日、The Guardian 2025年12月下旬など）。
4. **サンプル・方法**：新規に作った**YouTubeアカウント1つ**で、ショートフィードの最初の500本を分類した。AI生成104本（20.8%→21%）、ブレインロット165本（33%）。別に、各国のトレンド上位100チャンネル、計約15,000チャンネルを調べ、AIスロップだけのチャンネル278件を特定。再生数・推定収益は Social Blade の推計値。
5. **調査主体・利害関係**：Kapwing。AI機能付きのオンライン動画編集ツールの販売会社。デジタルPR会社 NeoMam と組んだコンテンツマーケティング型の調査で、話題を作る目的がある。
6. **一次情報での表現**：最初の500本のうち104本（21%）がAI生成、165本（33%）がブレインロット。レポート自体は「21〜33% of YouTube's feed may consist of AI slop or brainrot」と表現している。
7. **注意点**
   - n=1アカウント、1回の試行。地域・時刻・端末の条件は未確認。
   - 「AIスロップ」の判定基準と、誰が判定したかは確認できなかった。
   - 対象はショートのフィードで、YouTube全体ではない。
   - 一部報道の「21.33%」は「21〜33%」の誤記と考えられる。

### B2. 米国成人の49%が、フィードのAIコンテンツが増えたらSNS利用を減らす・やめる（Story Radius）
1. **判定**：一次情報見つからず
2. **一次情報**
   - 見つからなかった。数字は eMarketer「YouTube’s AI slop surge risks brand safety and viewer trust」 https://www.emarketer.com/content/youtube-ai-slop-surge-risks-brand-safety-viewer-trust （依頼記載URLと同じ。直接アクセスは不可）と、eMarketer の別記事（ブランドセーフティFAQ）で「per Story Radius」として引用されている。
   - Story Radius 公式サイト https://www.storyradius.com/ には「AI生成動画のSNS利用についての新しい調査」の告知バナーがあるだけで、報告書本体・方法論は見つからなかった。
3. **調査時期・公開日**：不明。
4. **サンプル・方法**：不明（サンプル数・実査時期・パネルとも確認できない）。
5. **調査主体・利害関係**：Story Radius は映像・コンテンツ制作会社（自己紹介は「production company」）。人間が作るコンテンツの価値を主張することに利害がある。eMarketer の FAQ記事では DoubleVerify と並べて書かれているが、DoubleVerify との関係は確認できなかった。
6. **二次情報での表現**：「49% of US adults would use social platforms less—or stop using them altogether—if the amount of AI content in their feeds grew」（eMarketer、per Story Radius）。同じ箇所に「85%が不気味の谷の要素で没入が途切れる」という数字もある。
7. **注意点**
   - DoubleVerify の別調査（22市場・消費者22,000人）や、「シンガポールの消費者の49%」という別の数字と混同しやすい。
   - 「減らす」と答えたのは仮定の質問に対する意向で、実際の行動を測ったものではない。

### B3. AI製広告をAIだと確信できた視聴者は13%、人間製広告をAIと疑った割合も同じ（Ipsos×シラキュース大学）
1. **判定**：一部相違（大学の公式リリースとは一致。共同調査者 Ipsos の公式ページとは数字が食い違う）
2. **一次情報**
   - Syracuse University News「Newhouse Research Finds AI Ads Fall Short on Sales Impact」（2026年5月18日） https://news.syr.edu/2026/05/18/newhouse-research-finds-ai-ads-fall-short-on-sales-impact/
   - Newhouse School「AI Ads Are Almost Indistinguishable From Human-Made Work. They Just Don’t Perform as Well.」 https://newhouse.syracuse.edu/news/ai-ads-are-almost-indistinguishable-from-human-made-work-they-just-dont-perform-as-well/
   - Ipsos「AI Ads Are Good Enough — And That’s the Problem」 https://www.ipsos.com/en-us/ai-ads-are-good-enough-and-thats-problem
   - 同PDF https://www.ipsos.com/sites/default/files/ct/publication/documents/2026-05/Ipsos_SU_POV-AI_Ads_Just_Good_Enough.pdf
   - 依頼記載URL（greyjournal.net）：アクセス不可。検索でも該当箇所は確認できなかった。
3. **調査時期・公開日**：2026年5月公開。
4. **サンプル・方法**：米国の消費者3,000名。10ブランド（Cheerios、Chewy、Febreze、Fiat、H&M、Old Navy、Herbal Essences、Ray-Ban Meta、TurboTax、Visa）の広告20本（人間製10本／AI製10本）を Ipsos Creative|Spark で評価。AI広告は Gemini で元の企画書を逆算して作った。
5. **調査主体・利害関係**：Ipsos（調査会社。Creative|Spark は自社の有償の広告評価ツール）と、Syracuse大学 Newhouse School の教員による共同調査。Ipsos には、自社ツールのベンチマークの有用性を示すという利害がある。
6. **一次情報での表現**
   - Syracuse大学リリース：「Only 13% of viewers who saw an AI-generated ad were at least somewhat confident it was made by AI—the same share as viewers who suspected human-made ads were AI-generated」。40%はどちらとも判断できなかった。
   - Ipsos 公式ページ（検索抜粋による）：「Only 25% of AI ad viewers were at least somewhat confident the spot was AI-made」。40%は判断できなかった。
   - 効果：人間製の広告は短期効果で14%、長期効果で17%強い（Ipsos）。ベンチマーク比では人間製+11ポイント、AI製−5ポイント（Syracuse大学）。
7. **注意点**
   - **同じ調査の一次資料で13%と25%が併存している。** 集計の切り口（設問・母数）の違いなのか誤記なのかは、PDF本体を直接確認しないと判断できない。主張は大学側の数字だけを採っている。
   - 評価は広告評価ツール上での反応で、実際の視聴環境とは違う。

---

## C. プラットフォームの規約・収益化

### C1. YouTubeは2025年7月15日から、大量生産・反復的なコンテンツの収益化ルールを改定
1. **判定**：確認済み
2. **一次情報**：YouTube ヘルプ「YouTube channel monetization policies」 https://support.google.com/youtube/answer/1311392?hl=en （依頼に出典URLの記載なし）
3. **公開日**：2025年7月15日に適用。
4. **サンプル・方法**：該当なし（規約）。
5. **主体・利害関係**：プラットフォーム公式。
6. **一次情報での表現**：「repetitious content」ポリシーを「inauthentic content」に改称し、大量生産されたもの・反復的なものを含むことを明確にした。テンプレートで量産したような、作り手独自の視点がないAI生成コンテンツは対象になる。AIの利用そのものは収益化の妨げにならない。
7. **注意点**
   - YouTube 側（Rene Ritchie 氏）は「長年あるガイドラインの小さな更新」と説明していた。報道では「AI一掃」のような大きな変更として扱うものもあり、解釈が割れている。
   - 「BGMの追加や速度変更だけでは不十分」といった細かい基準は二次報道の記述で、公式の文言かどうかは未確認。
   - 再利用コンテンツ（reused content）ポリシーは別で、変更されていない。

### C2. Instagramの「Reels Play Bonus」は新規クリエイターには提供されていない／招待制
1. **判定**：確認済み（ただし Meta 公式ページは見つからず、報道に載った Meta 広報の声明による）
2. **一次情報**
   - Meta 広報の声明（2023年3月）を引用した報道：BuzzFeed News「Creators Say The End of Meta’s Reels Bonus Program Is A “Monumental” Blow…」 https://www.buzzfeednews.com/article/kelseyweekman/reels-play-bonus-ending-creators-speak-out
   - Tubefilter（2024年4月5日） https://www.tubefilter.com/2024/04/05/instagram-spring-bonus-creator-monetization/
   - 依頼記載URL（aicontentdrop.com）：二次記事。アクセス不可。
3. **時期**：2023年3月に新規・更新の契約を停止（既存の契約は履行）。
4. **サンプル・方法**：該当なし。
5. **主体・利害関係**：Meta 広報の声明。
6. **一次情報での表現**：Meta は「new or renewed」の Reels Play bonus 契約は提供しないとした。理由は「monetization solutions」群への投資に移るため。制度はもともと招待制だった（米国のInstagramと、各国のFacebookが対象）。
7. **注意点**
   - 主張の「新規には提供されていない」は事実に合うが、実態は2023年の時点で制度が事実上終了していることで、表現がそれを弱めている。
   - 2024年以降の「Spring Bonus」など後継のテストは別の制度。
   - 「韓国・日本では存続」とする2026年のガイドの記述は、一次情報で確認できなかった。

### C3. Metaは2026年3月13日にオリジナルでないコンテンツのポリシーを公表
1. **判定**：確認済み（対象はFacebook。Instagramへの拡大は別の日付）
2. **一次情報**
   - Meta Newsroom「Rewarding Original Creators on Facebook」 https://about.fb.com/news/2026/03/rewarding-original-creators-on-facebook/
   - Facebook Creators ブログ「Supporting original content on Facebook」 https://creators.facebook.com/blog/supporting-original-content-on-facebook （2026年3月13日付）
   - 依頼記載URL（blog.evolvedlotus.com）：二次記事。アクセス不可。
3. **公開日**：2026年3月13日。
4. **サンプル・方法**：該当なし。
5. **主体・利害関係**：プラットフォーム公式。
6. **一次情報での表現**：「Creators who are not adding substantial creative value will see their content deprioritized, and they may see their account deemed non-recommendable and demonetized」。オリジナルのリールは2025年下半期に、前年同期比で再生数・視聴時間とも約2倍になったとしている。
7. **注意点**
   - 3月13日の発表は**Facebookが対象**。Instagramで、写真・カルーセルの転載アカウント（アグリゲーター）を推薦対象から外したのは2026年4月30日ごろ（Mosseri 氏の動画、報道による）。依頼記載URLの記事題名は Instagram リールなので、プラットフォームを取り違えないよう注意。
   - Facebookの転載ペナルティ自体は2025年7月から始まっている。

### C4. Metaのオリジナリティ施策で、オリジナル投稿者のリーチ+40〜60%、転載系AIアカウントは−60〜80%（Social Media Today）
1. **判定**：一次情報見つからず（出典の帰属も誤り）
2. **一次情報**
   - 見つからなかった。Social Media Today の該当記事「Instagram updates algorithm to benefit original creators」 https://www.socialmediatoday.com/news/instagram-updates-algorithm-to-benefit-original-creators/819016/ はポリシーの内容を報じているが、40〜60%・60〜80%という数字は検索結果では確認できなかった。
   - 数字の出どころとして確認できたのは、マーケ会社ブログ Crossglobe Marketing「Instagram's 2026 Algorithm Punishes Reposts — Here's Proof」 https://crossglobemarketing.com/blogs/instagram-original-content-algorithm-2026/ 。
   - 依頼記載URL（alici.ai）：二次記事。アクセス不可。
3. **時期**：2026年4月の施策開始後の観測とされる。
4. **サンプル・方法**：不明。Meta が公表したデータではない。
5. **主体・利害関係**：マーケ支援会社のブログ。依頼記載の alici.ai は AIインフルエンサー関連のサービス。
6. **二次情報での表現**：「original content now sees 40-60% more distribution than reposted content, while aggregator accounts recorded 60-80% reach drops」（Crossglobe）。
7. **注意点**
   - Meta は効果の大きさを数字で公表していない。
   - 別のブログは「50〜70%減」としており、推計値どうしでも一致しない。
   - 主張の「転載系**AI**アカウント」という限定は、どの資料にも見当たらない。

### C5. Instagramが2026年5月4日に任意の「AI creator」ラベルのテストを開始
1. **判定**：確認済み（Instagram 公式の発表ページは見つからず、報道とアプリ内メッセージによる）
2. **一次情報（に近い報道）**
   - Engadget「Instagram is testing optional 'AI creator' labels」（2026年5月4日） https://www.engadget.com/2162426/instagram-is-testing-optional-ai-creator-labels/
   - 依頼記載URL（yourstory.com）：二次記事。アクセス不可。
3. **公開日**：2026年5月4日に報道。
4. **サンプル・方法**：該当なし。
5. **主体・利害関係**：プラットフォームの機能テスト（報道ベース）。
6. **報道での表現**：アカウント単位の任意ラベル。プロフィール、フィード投稿・リールのユーザー名の下に表示される。投稿単位の「AI info」ラベルが付く場合はそちらが優先。ランキングや推薦には影響しないと説明されている。
7. **注意点**
   - 一部の報道は「AI-Author」という呼び名を使っている。
   - 後に「AI-generated profile」に改称され、未表示のアカウントは推薦から外されるという報道もあるが、日付と一次情報は未確認。検証日時点では、テストのときと仕様が変わっている可能性がある。

---

## D. 市場・単価

### D1. YouTubeの国別CPM：オーストラリア $36.21、米国 $32.75、インド $1未満
1. **判定**：一次情報見つからず（Google は国別CPMを公表していない。数字の出どころは民間の推計）
2. **一次情報**
   - 公式データは存在しない。$36.21／$32.75 は Lenos（YouTube向けツールサイト）の推計と一致する。 https://www.lenostube.com/en/youtube-cpm-rpm-rates/ （theloops.live の比較表ではLenosの2026年4月2日版として扱われている）
   - 依頼記載URL（upgrowth.in）：アクセス不可。検索でも該当ページの中身は確認できなかった。
3. **時期**：2026年（Lenosの2026年4月2日版とされる）。
4. **サンプル・方法**：Lenos の方法論とサンプルは非公開・未確認。
5. **主体・利害関係**：Lenos はYouTube関連ツールのサイト。upgrowth.in はインドのグロースマーケティング会社。いずれも推計を集客に使う立場にある。
6. **推計値**
   - Lenos：オーストラリア CPM $36.21／RPM $11.95、米国 CPM $32.75／RPM $10.81。
   - インド：Lenos の値は未確認。他の推計では MilX $0.74、YT Money Calculator $0.60〜1.40 など、$1前後〜それ以下。
7. **注意点**
   - 推計どうしの差が大きい。MilX は米国 $14.67、オーストラリア $13.30。CreatiCalc は米国 $6〜20。同じ国で3倍程度の差がある。
   - 広告主が払うCPM、再生ベースのCPM、クリエイターのRPMのどれを指すのか、明記していない推計が多い。

### D2. 日本のCPMは推計によって約$2〜3台から$10台までばらつく（複数推計の比較と、差が出る理由）
1. **判定**：確認済み（推計値に大きなばらつきがあることは確認できた。公式の値は存在しない）
2. **推計の一覧**（いずれも民間の推計。Google の公式値ではない）

| 出典 | 日本 CPM | 日本 RPM | 備考 |
|---|---|---|---|
| Lenos https://www.lenostube.com/en/youtube-cpm-rpm-rates/ | $10.53 | $2.90 | 同じページ内の別の平均値はもっと低いとの指摘あり |
| SR Zone https://www.thesrzone.com/2025/07/youtube-cpm-cpc-rates-by-country.html | $11.58 | — | 最も高い値 |
| Dynamoi https://dynamoi.com/data/youtube-adsense-rpm/jp | 再生CPM 約$5.95 | $3.10 | |
| TubeAnalytics https://www.tubeanalytics.net/benchmarks/japan | 約$5.00 | 約$2.50 | |
| MilX https://milx.app/en/cases/in-what-countries-cpm-are-the-highest | $5.68 | $2.00〜3.10 | 20位 |
| CreatiCalc https://creaticalc.com/blog/youtube-cpm-rates-by-country | $2〜6 | $1〜3 | |
| Fluxnote https://fluxnote.io/guides/youtube-earnings-by-country-comparison | — | $1.10〜3.30 | 1,000再生あたりの収益 |
| AIR Media-Tech https://air.io/en/monetization/what-rpm-can-you-expect-from-shorts-in-2026 | — | **ショート** RPM 約$0.144 | ショートは長尺より1〜2桁低い |
| 国内広告代理店の記事（mobinc.jp 等） | 300〜700円、400〜600円 | — | 広告主が払う出稿単価 |

3. **時期**：2025〜2026年の各推計。
4. **サンプル・方法**：ほぼすべて方法論が非公開か、詳細が不明。
5. **主体・利害関係**：収益計算ツール、YouTube分析ツール、広告代理店など。いずれも推計を集客に使う立場。
6. **差が出る理由**（各推計の注記・定義から確認できる範囲）
   - **CPMとRPMの混同**：CPMは広告表示1,000回あたりの広告収入（YouTubeの取り分を差し引く前）。RPMは1,000再生あたりのクリエイター収入（取り分を差し引いた後で、広告が出ない再生も含む）。RPMはCPMの約40〜60%とされる。「$2〜3台」の多くはRPMの値で、CPMと並べると見かけ上の差が大きくなる。
   - **CPMの種類**：YouTube Analytics には CPM と 再生ベースCPM（Playback-based CPM）がある。広告主側の出稿CPM（Google広告の入札単価）も同じ「CPM」と呼ばれる。
   - **長尺とショートの違い**：ショートのRPMは1,000エンゲージビューあたりで計算され、桁違いに低い（約$0.14）。
   - **ジャンルの構成**：金融・ビジネスは娯楽・ゲームの数倍と、どの推計も書いている。サンプルに含まれるチャンネルのジャンルで平均値が変わる。
   - **季節性・時点**：第4四半期は高い（インドでは第1四半期より40〜80%高いとの推計）。どの時点の値かで変わる。
   - **データ元**：自社ツールのユーザー集計、アンケート、他サイトの数字の転載が混ざっている。
7. **注意点**：検証できる公式値がないため、どの値も「推計の一つ」として扱う必要がある。確かな値は、各チャンネルの YouTube Studio にある地域別収益でしか得られない。

### D3. AI ASMRのガラス切断フォーマットは2026年時点で成熟期
1. **判定**：一次情報見つからず（出典のブログにそういう主張はあるが、裏付けとなるデータがない）
2. **情報源**
   - 依頼記載URL：https://aiimagetovideo.pro/ja/blog/ai-asmr-video/ （日本語版はアクセス不可。英語版 https://aiimagetovideo.pro/blog/ai-asmr-video/ の検索抜粋で確認）
   - 流行の経緯：Fast Company「AI-generated ASMR is taking over the internet…」 https://www.fastcompany.com/91353440/ai-generated-asmr-is-taking-over-tiktok
3. **時期**：流行は2025年半ば（Google Veo 3 の公開後）から。ブログは2026年向けの記事。
4. **サンプル・方法**：なし（筆者の見解）。
5. **主体・利害関係**：aiimagetovideo.pro は AI動画生成ツールのサイト。AI ASMR制作を勧めることに直接の利害がある。
6. **出典での表現**（英語版）：「Glass cutting is maturing, but survival ASMR, dream beds, and newer formats are still wide open」「This is the most established AI ASMR format」。
7. **注意点**
   - 英語版の表現は「maturing（成熟しつつある）」で、「成熟期」と言い切ってはいない。
   - 再生数の推移や投稿数などの定量データはどこにも見つからなかった。Dexerto などは繰り返しの多さへの飽きの声を報じているが、これも定性的な話にとどまる。
   - 流行の段階を判断する根拠が、ツール販売会社の宣伝記事しかない。

---

## 出典の信頼性一覧

### 信頼性の高い出典
| 出典 | 種別 | 関連ID |
|---|---|---|
| YouTube ヘルプ（support.google.com/youtube/answer/1311392） | プラットフォーム公式 | C1 |
| Meta Newsroom（about.fb.com）・Facebook Creators ブログ | プラットフォーム公式 | C3 |
| Computers & Education（Otto, 2025） | 査読論文 | A7 |
| Frontiers in Psychology（Zhang ほか, 2026）／Telematics and Informatics（Chen ほか, 2024） | 査読論文（中国の若年層、横断研究が中心） | A6 |
| Syracuse University News／Newhouse School | 大学の公式リリース（Ipsos との共同） | B3 |
| LINEリサーチ（PR TIMES・公式note） | 大規模パネル調査（n=5,257、方法を開示） | A4 |

### 扱いに注意が必要な出典
| 出典 | 理由 | 関連ID |
|---|---|---|
| コムニコ | SNSマーケ会社。ショート動画制作プランを販売しており、自社に関係する領域の自社調査 | A1 |
| Clutch | 制作会社・マーケ会社の送客プラットフォーム。サンプル数の表記が一致しない。23%の出典が不明 | A2 |
| 株式会社LIH | n=64、男性85.9%、Googleフォームの便宜的サンプル。事業内容は未確認 | A3 |
| ベクトル | PR会社。ショート動画ラボ設立の告知を兼ねた調査で、見出しが本文の数字より強い | A5 |
| Kapwing（＋NeoMam Studios） | AI機能付き動画編集ツールの会社と、デジタルPR会社によるコンテンツマーケ型調査。アカウント1つでの試行 | B1 |
| Story Radius（eMarketer 経由） | 映像制作会社。報告書本体と方法論が見つからない | B2 |
| Ipsos（Creative|Spark） | 自社の有償ツールで評価。共同調査の大学リリースと数字が食い違う | B3 |
| Crossglobe Marketing ほかマーケブログ | 根拠を示さないリーチ増減の数字。Social Media Today 発と誤って帰属されている | C4 |
| Lenos／upgrowth.in／MilX／CreatiCalc／SR Zone ほか収益計算サイト | 方法論が非公開の推計。CPMとRPMの定義が混在 | D1, D2 |
| aiimagetovideo.pro | AI動画生成ツールの販売サイトの宣伝記事 | D3 |
| 依頼記載の二次まとめ記事（commercepick.com、ecnomikata.com、primetimer.com、greyjournal.net、aicontentdrop.com、blog.evolvedlotus.com、alici.ai、yourstory.com、upgrowth.in） | 二次情報。今回はすべて直接アクセスできず、内容は未照合 | 各項 |
