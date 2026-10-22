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

CONCEPTS = {"rain": RAIN, "snow": SNOW, "ocean_sleep": OCEAN_SLEEP}
