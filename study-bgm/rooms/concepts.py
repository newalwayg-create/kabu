"""動画ごとのコンセプト設定.

1 つのコンセプト = 曲 (コード・楽器・構成) + 効果音 + サムネイル + タイトル・説明文.
新しい動画を作るときは、ここに辞書を 1 つ足して `python3 make_room.py <名前>` を実行する.

パートの種類 (parts の kind):
    sustain  コードを白玉で伸ばす (パッド・ストリングス・クワイア)
    bass     ルート音を長く
    drone    ルート + 5 度の低いうなり
    arp      和音を 1 音ずつゆっくり分散 (ピアノなど)
    comp     和音を軽く鳴らして伸ばす (エレピなど)
    sprinkle コード構成音寄りの音をまばらに置く (ヴィブラフォン・チェレスタなど)

章の parts で "名前@late" と書くと、その章の後半だけ鳴る.
dark は 0 = 明るい (こもらない) 〜 1 = 暗い (強くこもる) で、章の始め→終わりを指定する.
"""
from make_bgm import CHORDS as LOFI_CHORDS
from make_ocean import CHORDS as OCEAN_CHORDS
from make_ocean import VIBES_SCALE as D_DORIAN

RAIN = dict(
    word="Rain.",
    subtitle="SOFT PIANO & RAIN",
    scene="rain",
    title="Rain. | Soft Piano & Rain Ambient Music for Sleep, Study & Meditation",
    alt_titles=[
        "A Quiet Night by the Window | Soft Piano & Rain Ambient Music for Sleep, Study & Meditation",
        "Rain.",
    ],
    lead="Rain. — an hour by a rainy window at night, with soft piano and slow strings.",
    use_line="Calm ambient music with rain sounds for sleep, study and meditation.",
    credits="Original composition. Piano, Rhodes, warm pads, strings and fretless bass,\n"
            "with rain on the glass, slow drips and distant thunder.",
    tags="#ambient #rainsounds #studymusic",
    minutes=60,
    bpm=66,
    bars_per_chord=2,
    lowpass=(7000, 1600),
    chords={
        "Ebmaj9":  (39, [55, 58, 62, 65]),
        "Cm9":     (36, [51, 55, 58, 62]),
        "Abmaj9":  (44, [55, 60, 63, 70]),
        "Bbsus":   (46, [56, 60, 63, 65]),
        "Fm9":     (41, [51, 56, 60, 67]),
        "Gm7":     (43, [53, 58, 62, 67]),
        "Dbmaj7":  (37, [53, 56, 60, 63]),
    },
    scale=[63, 65, 67, 70, 72, 74, 75, 77, 79, 82],  # E♭ メジャー・ペンタ寄り
    parts={
        "pad":      dict(kind="sustain", prog=89, vel=42),
        "strings":  dict(kind="sustain", prog=49, vel=40, octave=12, drop_root=True),
        "bass":     dict(kind="bass", prog=35, vel=62),
        "piano":    dict(kind="arp", prog=0, vel=50, step=1.0),
        "piano_hi": dict(kind="sprinkle", prog=0, vel=44, octave=0, counts=[0, 1, 1, 2]),
        "rhodes":   dict(kind="comp", prog=4, vel=50),
    },
    chapters=[
        dict(name="First Drops",  label="First Drops",   prog=["Ebmaj9", "Cm9", "Abmaj9", "Bbsus"], weight=1.0, parts=["pad", "piano_hi"], dark=(0.3, 0.2)),
        dict(name="By the Window", label="By the Window", prog=["Ebmaj9", "Cm9", "Abmaj9", "Bbsus"], weight=2.0, parts=["pad", "bass", "piano"], dark=(0.2, 0.2)),
        dict(name="Steady Rain",  label="Steady Rain",   prog=["Fm9", "Gm7", "Abmaj9", "Dbmaj7"], weight=2.0, parts=["pad", "bass", "piano", "strings@late"], dark=(0.2, 0.35)),
        dict(name="Lamplight",    label="Lamplight",     prog=["Abmaj9", "Ebmaj9", "Fm9", "Bbsus"], weight=2.0, parts=["pad", "bass", "rhodes", "piano_hi"], dark=(0.35, 0.35)),
        dict(name="Downpour",     label="Downpour",      prog=["Cm9", "Abmaj9", "Ebmaj9", "Bbsus"], weight=2.0, parts=["pad", "bass", "strings", "piano"], dark=(0.35, 0.5)),
        dict(name="After the Rain", label="After the Rain", prog=["Fm9", "Gm7", "Abmaj9", "Dbmaj7"], weight=2.0, parts=["pad", "bass", "rhodes", "piano_hi"], dark=(0.5, 0.3)),
        dict(name="Last Drops",   label="Last Drops",    prog=["Ebmaj9", "Cm9", "Abmaj9", "Bbsus"], weight=1.0, parts=["pad", "piano_hi"], dark=(0.3, 0.3)),
    ],
    sfx=[
        dict(type="rain", level=0.022),
        dict(type="drips", level=0.05, every=(6, 18)),
        dict(type="thunder", level=0.22, every=(240, 540)),
    ],
    sfx_reverb=0.3,
)

SNOW = dict(
    word="Snow.",
    subtitle="QUIET WINTER AMBIENT",
    scene="snow",
    title="Snow. | Quiet Winter Ambient Music for Sleep, Study & Meditation",
    alt_titles=[
        "A Cabin in the Snow | Winter Ambient Music with Wind & Fireplace for Sleep, Study & Meditation",
        "Snow.",
    ],
    lead="Snow. — an hour in a quiet cabin while the snow falls outside.",
    use_line="Calm winter ambient music for sleep, study and meditation.",
    credits="Original composition. Celesta, piano, slow strings and warm pads,\n"
            "with soft wind outside and a crackling fireplace.",
    tags="#ambient #wintermusic #studymusic",
    minutes=60,
    bpm=62,
    bars_per_chord=2,
    lowpass=(7500, 1800),
    chords={
        "Dmaj9":    (38, [54, 57, 61, 64]),
        "Bm9":      (35, [50, 54, 57, 61]),
        "Gmaj7#11": (43, [54, 59, 61, 62]),
        "Asus4":    (45, [52, 57, 59, 62]),
        "Em9":      (40, [55, 59, 62, 66]),
        "F#m7":     (42, [52, 57, 61, 64]),
        "Cmaj7":    (36, [52, 55, 59, 62]),
    },
    scale=[66, 69, 71, 73, 74, 76, 78, 81, 83, 85],  # D メジャー (リディアン寄り)
    parts={
        "pad":     dict(kind="sustain", prog=89, vel=42),
        "strings": dict(kind="sustain", prog=49, vel=38, octave=12, drop_root=True),
        "bass":    dict(kind="bass", prog=32, vel=58),
        "piano":   dict(kind="arp", prog=0, vel=46, step=1.5),
        "celesta": dict(kind="sprinkle", prog=8, vel=50, octave=0, counts=[0, 1, 2, 2]),
        "box":     dict(kind="sprinkle", prog=10, vel=40, octave=0, counts=[0, 0, 1, 1], prob=0.6),
        "choir":   dict(kind="sustain", prog=52, vel=32, octave=12, drop_root=True),
    },
    chapters=[
        dict(name="First Snow",   label="First Snow",    prog=["Dmaj9", "Bm9", "Gmaj7#11", "Asus4"], weight=1.0, parts=["pad", "celesta"], dark=(0.3, 0.25)),
        dict(name="Fireside",     label="Fireside",      prog=["Dmaj9", "Bm9", "Gmaj7#11", "Asus4"], weight=2.0, parts=["pad", "bass", "piano"], dark=(0.25, 0.25)),
        dict(name="Frost",        label="Frost on the Glass", prog=["Em9", "F#m7", "Gmaj7#11", "Cmaj7"], weight=2.0, parts=["pad", "bass", "celesta", "strings@late"], dark=(0.25, 0.4)),
        dict(name="Snowfall",     label="Snowfall",      prog=["Gmaj7#11", "Dmaj9", "Em9", "Asus4"], weight=2.0, parts=["pad", "bass", "piano", "box"], dark=(0.4, 0.4)),
        dict(name="Long Night",   label="The Long Night", prog=["Em9", "F#m7", "Gmaj7#11", "Cmaj7"], weight=2.0, parts=["pad", "bass", "strings", "choir@late"], dark=(0.4, 0.55)),
        dict(name="Embers",       label="Embers",        prog=["Dmaj9", "Bm9", "Gmaj7#11", "Asus4"], weight=2.0, parts=["pad", "bass", "piano", "celesta"], dark=(0.55, 0.35)),
        dict(name="Morning",      label="Snow at Dawn",  prog=["Gmaj7#11", "Dmaj9", "Em9", "Asus4"], weight=1.0, parts=["pad", "celesta"], dark=(0.35, 0.3)),
    ],
    sfx=[
        dict(type="wind", level=0.013),
        dict(type="fire", level=0.013),
    ],
    sfx_reverb=0.0,
)

OCEAN_SLEEP = dict(
    word="Ocean.",
    subtitle="3 HOURS · DEEP SLEEP",
    scene="ocean_dark",
    title="Ocean. | 3 Hours of Deep Sea Ambient Music for Deep Sleep",
    alt_titles=[
        "Ocean. | Deep Sea Ambient Music for Sleep · 3 Hours, No Sudden Sounds",
        "Ocean.",
    ],
    lead="Ocean. — three hours of slow descent into the deep sea, made for sleep.",
    use_line="Dark, gentle deep sea ambient music for deep sleep and rest. No sudden sounds.",
    credits="Original composition. Pads, fretless bass, a low drone, vibraphone and choir,\n"
            "with soft waves and the occasional quiet bubble.",
    tags="#sleepmusic #ambient #deepsleep",
    minutes=180,
    bpm=54,
    bars_per_chord=2,
    lowpass=(5000, 650),
    chords=OCEAN_CHORDS,
    scale=D_DORIAN,
    parts={
        "pad":   dict(kind="sustain", prog=94, vel=46),
        "bass":  dict(kind="bass", prog=35, vel=60),
        "drone": dict(kind="drone", prog=89, vel=40),
        "vibes": dict(kind="sprinkle", prog=11, vel=48, octave=-12, counts=[0, 1, 1], prob=0.6),
        "choir": dict(kind="sustain", prog=52, vel=30, octave=12, drop_root=True),
    },
    chapters=[
        dict(name="Surface",  label="Surface",       prog=["Dm9", "Bbmaj7#11", "Gm9", "A7sus4b9"], weight=1.0, parts=["pad", "vibes"], dark=(0.1, 0.2)),
        dict(name="Descent",  label="Descent",       prog=["Dm9", "Bbmaj7#11", "Gm9", "A7sus4b9"], weight=2.0, parts=["pad", "bass", "vibes"], dark=(0.2, 0.8)),
        dict(name="Deep 1",   label="The Deep",      prog=["Ebmaj7#11", "Dm9", "Cmaj7#11", "Bbmaj7"], weight=6.0, parts=["pad", "bass", "drone", "vibes"], dark=(0.8, 0.9)),
        dict(name="Abyss 1",  label="The Abyss",     prog=["Dm9", "Ebmaj7#11", "Bbmaj7#11", "Ebmaj7#11"], weight=6.0, parts=["pad", "bass", "drone", "choir"], dark=(0.9, 0.95)),
        dict(name="Deep 2",   label="Deep Current",  prog=["Ebmaj7#11", "Dm9", "Cmaj7#11", "Bbmaj7"], weight=6.0, parts=["pad", "bass", "drone", "vibes"], dark=(0.95, 0.95)),
        dict(name="Abyss 2",  label="Stillness",     prog=["Dm9", "Ebmaj7#11", "Bbmaj7#11", "Ebmaj7#11"], weight=6.0, parts=["pad", "drone", "choir"], dark=(0.95, 0.95)),
    ],
    sfx=[
        dict(type="waves", level=0.018),
        dict(type="bubbles", level=0.035, every=(50, 140), min_dark=0.3),
    ],
    sfx_reverb=0.35,
    fade_out=60,
)

FOCUS = dict(
    # 2026-10-25: 最初の 4 本のデータ (クリック率 1.8%、平均視聴 3 分 14 秒) を受けて、
    # 弱点を直した版. 0:00 から完成形の音で始め、見せ方は猫の画像 + 気持ち型タイトルにする.
    word="Focus.",
    image="youtube/assets/cat_tornado.png",          # sage の余白で正方形のまま使う
    still="youtube/assets/window_cat.jpg",           # 動画の背景 (2026-10-25: 左右の緑の余白を避けて 16:9 の一枚絵に)
    extra_thumbs={"vortex": "rooms/out/rain/thumb_cat_vortex.png",
                  "window": "youtube/assets/window_cat.jpg"},
    title="when your head won't stop spinning | calm music to focus & study",
    alt_titles=[
        "Focus. | Soft Rhodes & Piano Music for Deep Work and Study (1 Hour)",
        "my brain after 6 hours of studying | calm focus music",
    ],
    lead="When your head won't stop spinning — an hour of calm, steady music to settle in and focus.",
    use_line="Soft Rhodes, piano and a gentle beat for studying, deep work and reading.",
    credits="Original composition. Rhodes, soft piano, warm pads, bass and light drums.\n"
            "No talking. Starts right away.",
    tags="#studymusic #focusmusic #ambient",
    minutes=60,
    bpm=72,
    bars_per_chord=1,
    fade_in=1.0,
    lowpass=(6500, 1800),
    chords=LOFI_CHORDS,
    scale=[60, 62, 65, 67, 69, 72, 74, 77],  # F メジャー・ペンタ
    parts={
        "pad":    dict(kind="sustain", prog=89, vel=38),
        "rhodes": dict(kind="comp", prog=4, vel=54),
        "bass":   dict(kind="bass", prog=33, vel=60),
        "piano":  dict(kind="arp", prog=0, vel=40, step=0.5),
        "vibes":  dict(kind="sprinkle", prog=11, vel=44, octave=12, counts=[0, 1, 1, 2], prob=0.7),
        "drums":  dict(kind="drums", prog=0, vel=44, swing=0.56),
    },
    # 静かな導入は作らない. 最初の章から全部の楽器がそろっている
    chapters=[
        dict(name="Settle In",  label="Settle In",   prog=["Fmaj9", "Dm9", "Bbmaj9", "C13sus4"], weight=2.0, parts=["pad", "rhodes", "bass", "drums", "vibes"], dark=(0.15, 0.15)),
        dict(name="Deep Work",  label="Deep Work",   prog=["Am7", "Dm9", "Gm9", "C13sus4"], weight=2.0, parts=["pad", "rhodes", "bass", "drums", "piano"], dark=(0.15, 0.2)),
        dict(name="Flow",       label="Flow",        prog=["Bbmaj9", "Am7", "Gm9", "C13sus4"], weight=2.0, parts=["pad", "piano", "bass", "drums", "vibes"], dark=(0.2, 0.2)),
        dict(name="Second Wind", label="Second Wind", prog=["Fmaj9", "Dm9", "Bbmaj9", "C13sus4"], weight=2.0, parts=["pad", "rhodes", "bass", "drums", "piano"], dark=(0.2, 0.15)),
        dict(name="Long Haul",  label="The Long Haul", prog=["Am7", "Dm9", "Gm9", "C13sus4"], weight=2.0, parts=["pad", "rhodes", "bass", "drums", "vibes"], dark=(0.15, 0.2)),
        dict(name="Last Page",  label="Last Page",   prog=["Bbmaj9", "Am7", "Gm9", "C13sus4"], weight=2.0, parts=["pad", "rhodes", "piano", "bass", "drums"], dark=(0.2, 0.25)),
    ],
    sfx=[],
    sfx_reverb=0.0,
)

def transposed(chords, semitones):
    """コード表をまるごと移調する (同じ進行を別のキーで使い回すため)."""
    return {k: (r + semitones, [n + semitones for n in v]) for k, (r, v) in chords.items()}


def focus_variant(still, title, alt_titles, lead, bpm, semitones, lowpass, **extra):
    """窓辺の猫 (FOCUS) の型を、絵・タイトル・キー・テンポだけ変えて使い回す."""
    cfg = dict(FOCUS)
    cfg.pop("image", None)
    cfg.update(
        still=still, extra_thumbs={}, title=title, alt_titles=alt_titles, lead=lead,
        bpm=bpm, lowpass=lowpass,
        chords=transposed(LOFI_CHORDS, semitones),
        scale=[n + semitones for n in FOCUS["scale"]],
        **extra,
    )
    return cfg


# 2026-10-31: ミーム猫 3 枚 (ChatGPT で生成) × 窓辺の猫の曲の型. タイトルは隣に並ぶ動画にならった「ゆるい一言」型
MEME_SHOCK = focus_variant(
    still="youtube/assets/meme_cat_shock.png",
    title="when you realize the deadline is tomorrow | calm music to focus & study",
    alt_titles=["the deadline is tomorrow. | calm music to focus & study"],
    lead="When you realize the deadline is tomorrow — an hour of calm, steady music to get it done.",
    bpm=74, semitones=2, lowpass=(6500, 1800), word="Deadline.",
)
MEME_LOADING = focus_variant(
    still="youtube/assets/meme_cat_loading.png",
    title="my brain at 3am trying to study | lofi music to focus",
    alt_titles=["brain still loading... | lofi music to focus & study"],
    lead="My brain at 3am trying to study — an hour of soft, steady lofi to keep going.",
    bpm=70, semitones=-3, lowpass=(5500, 1600), word="Loading.",
)
MEME_JUDGE = focus_variant(
    still="youtube/assets/meme_cat_judge.png",
    title="you said you'd start studying an hour ago | calm focus music",
    alt_titles=["start studying. now. | calm focus music"],
    lead="You said you'd start studying an hour ago — here's an hour of calm, steady music. Go.",
    bpm=76, semitones=5, lowpass=(6500, 1800), word="Judged.",
)

CONCEPTS = {"rain": RAIN, "snow": SNOW, "ocean_sleep": OCEAN_SLEEP, "focus": FOCUS,
            "meme_shock": MEME_SHOCK, "meme_loading": MEME_LOADING, "meme_judge": MEME_JUDGE}
