+++
id = "01M1QDTV36M61KK2JKVW3QEYJC"
title = "r11 design: re-trial findings A-044 to A-048"
type = "docs"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:38Z"
aliases = ["crunk:T-0102"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/*.md", "docs/design/subsystems/*.md"]

[[acceptance]]
text = "given the findings, when the design tree is read, then each maps to a contract change"
bound = false
+++

Second batch of re-trial findings. A-045/A-047 root cause: the generated theme import empties the heuristic tw_theme parse; the mapping becomes self-derived when the tokens file is configured, with alpha-modifier stripping. A-046: explain must never leak a KeyError; -rgb companions group with their parent color. A-044: layers/radii optional. A-048: JSON artifacts drift-check on parsed content.

## Drop reason
- 2026-09-05: duplicate of T-0101 (created during a cwd mixup; T-0101 is the live r11 design ticket)
