+++
id = "01M5DFKY9JMQH3VQH5KQ9SKQ2Q"
title = "claims config knobs for eviction and flap guard"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T20:21:34Z"
updated = "2026-11-12T15:16:54Z"
labels = ["no-story"]
scope = ["crates/frob-worktree/**", "docs/**", "changelog.d/**", "crates/frob-ledger/**", "crates/frob/src/config.rs"]

[[acceptance]]
text = "Given a [claims] table in frob.toml with evict_human, evict_agent, evict_rate and flap_repeat_days, when the config is loaded, then each value is parsed with the documented default when absent"
bound = true

[[acceptance]]
text = "Given a configured flap_repeat_days, when flap_review runs, then the window uses the configured days instead of the FLAP_REPEAT_DAYS constant"
bound = true
+++

found while working ~6CVW7F9: evict_human, evict_agent, evict_rate, flap guard 14-day rule, feed activity idle into EvictContext
