+++
id = "01M43AYY70EPEM1YMACXEZW79B"
title = "grimble-sysdesign family GRAMMAR: first slice of rules in GRL"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:32:05Z"
updated = "2026-10-21T12:32:22Z"
idempotency_key = "crunk-plan-g_GRAMMAR"
labels = ["area:grimble"]
scope = ["packs/grimble-sysdesign/rules/grammar/**", "packs/grimble-sysdesign/tests/grammar/**", "packs/grimble-sysdesign/pack.toml", "crates/gob-packs/src/sysdesign.rs", "crates/gob-packs/tests/sysdesign_pack.rs", "docs/grimble/packs/grimble-sysdesign.md", "changelog.d/01M43AYY70EPEM1YMACXEZW79B.added.md"]

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
bound = false
+++

Follow-up to the grimble-sysdesign scaffold: grammar and language-design rules for projects that define a language or protocol. Source: the 102 v1 backlog tickets (cluster B1) imported under area:grimble by ~TM4E1PN. First slice in GRL with examples; split at pickup if above 8 points.
