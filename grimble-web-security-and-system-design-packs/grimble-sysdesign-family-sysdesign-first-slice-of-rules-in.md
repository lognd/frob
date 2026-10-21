+++
id = "01M43AYWCV2QDMK30527JKZD66"
title = "grimble-sysdesign family SYSDESIGN: first slice of rules in GRL"
type = "story"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:32:03Z"
updated = "2026-10-21T13:46:08Z"
idempotency_key = "crunk-plan-g_SYSDESIGN"
labels = ["area:grimble"]
scope = ["packs/grimble-sysdesign/rules/sysdesign/**", "packs/grimble-sysdesign/tests/sysdesign/**", "crates/gob-packs/src/sysdesign.rs", "crates/gob-packs/tests/sysdesign_pack.rs", "docs/grimble/packs/grimble-sysdesign.md", "packs/grimble-sysdesign/pack.toml", "changelog.d/01M43AYWCV2QDMK30527JKZD66.added.md", "packs/grimble-sysdesign/rules/**"]

[[links]]
kind = "blocked-by"
target = "01M43AYJ2RMDD8DGZ5Q060142M"

[[acceptance]]
text = "Given a model or code violating the first rule, when `grimble check` runs, then the finding fires with teaching text"
bound = true

[[acceptance]]
text = "Given the clean example, when `grimble rule test` runs, then it passes"
bound = true

[[acceptance]]
text = "Given an input the rule cannot decide, when run, then it is Unresolved, never clean"
bound = true
+++

Follow-up to the grimble-sysdesign scaffold: system-design rules over the model (capacity, failure, boundary and dependency declarations). Source: the 102 v1 backlog tickets (cluster B1) imported under area:grimble by ~TM4E1PN. First slice in GRL with examples; split at pickup if above 8 points.
