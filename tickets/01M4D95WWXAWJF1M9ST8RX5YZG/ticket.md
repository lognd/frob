+++
id = "01M4D95WWXAWJF1M9ST8RX5YZG"
title = "GX catalogue additions: volume channels, haptics toggle, time limits to 10x, subtitle 2 lines and 38-40 characters, text in images, Unicode glyph icons"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-08T08:13:20Z"
updated = "2026-10-08T08:13:20Z"
scope = ["changelog.d/**", "crates/crunk-spec/**", "crates/crunk-check/**"]

[[acceptance]]
text = "Given a game profile lacking a volume-channel declaration, when crunk check runs, then a GX finding names the guideline"
bound = false

[[acceptance]]
text = "Given every coverage key declared, when checked, then clean"
bound = false
+++

notes/research/lint-catalogue-2026-10-08.md 4.2 N24; notes/research/creators-games-2026-10-08.md 5.2 observation (each item has two or more voices among GAG, XAG and IGDA; none is in the crunk.md 6 GX row).
