+++
id = "01M4FCZ19XSPWE1EDABY6GKQPS"
title = "check --json on exit 1 returns data null and findings [] with every finding as text in error.message"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T03:57:58Z"
updated = "2026-10-09T05:08:57Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-check/**", "crates/frob/**", "crates/gob-cli/**", "changelog.d/**", "docs/design/cli.md"]

[[acceptance]]
text = "Given a repository with an Error finding, when frob check --json exits 1, then the envelope has ok false, the findings array carries every finding as structured objects and error.message is a one-line summary"
bound = true
+++

Hullbreach platform migration repro: CI summaries cannot read findings from the failing envelope.
