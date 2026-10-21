+++
id = "01M43AYVHQWDNSE66CY4VVXDW5"
title = "grimble-sysdesign family STORE: first slice of rules in GRL"
type = "story"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:32:02Z"
updated = "2026-10-21T13:21:30Z"
idempotency_key = "crunk-plan-g_STORE"
labels = ["area:grimble"]
scope = ["packs/grimble-sysdesign/rules/store/**", "packs/grimble-sysdesign/tests/store/**", "packs/grimble-sysdesign/pack.toml", "crates/gob-packs/src/sysdesign.rs", "crates/gob-packs/tests/sysdesign_pack.rs", "docs/grimble/packs/grimble-sysdesign.md", "changelog.d/01M43AYVHQWDNSE66CY4VVXDW5.added.md"]

[[links]]
kind = "blocked-by"
target = "01M43AYJ2RMDD8DGZ5Q060142M"

[[acceptance]]
text = "Given a model or code violating the first rule, when `grimble check` runs, then the finding fires with teaching text"
bound = true

[[acceptance]]
text = "Given the clean example, when `grimble rule test` runs, then it passes"
bound = false

[[acceptance]]
text = "Given an input the rule cannot decide, when run, then it is Unresolved, never clean"
bound = false
+++

Follow-up to the grimble-sysdesign scaffold: data store design rules (schema, indexing, retention, consistency declarations). Source: the 102 v1 backlog tickets (cluster B1) imported under area:grimble by ~TM4E1PN. First slice in GRL with examples; split at pickup if above 8 points.
