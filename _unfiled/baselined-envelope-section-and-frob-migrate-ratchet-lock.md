+++
id = "01M66G70F82EC8EERE0077QKVV"
title = "baselined envelope section and frob migrate ratchet-lock hook"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-30T13:32:59Z"
updated = "2026-10-30T21:57:46Z"
scope = ["crates/frob/**", "crates/frob-check/**", "docs/reference/**", "docs/schemas/**", "crates/grimble-ci/**"]

[[acceptance]]
text = "baselined findings appear in the envelope baselined section; frob migrate converts frob-ratchet.lock.json once"
bound = true
+++

Follow-up of ~7FDF275. Quoted scope cut: route Baseline::partition output into the 'baselined' envelope section with per-rule remaining totals, wire a BaselineHost for BASE001/BASE002 (head/base-tip file, ticket liveness), and call migrate_ratchet_lock from 'frob migrate'.
