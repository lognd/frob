+++
id = "01M7AV6DMGJBMR5ATRTSEWGFDJ"
title = "Definition of Ready/Done: refuse close with empty acceptance criteria"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:17:34Z"
updated = "2026-11-13T17:24:05Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/**", "crates/frob-evidence/**", "crates/frob/tests/**", "crates/frob-land/tests/**", "docs/**"]

[[acceptance]]
text = "Closing done with no acceptance criteria fails unless explicitly waived."
bound = true
+++

H5: 21 percent of tickets closed done since Oct 30 had no acceptance criteria. Source: frob-audit-meta.md (Opus audit).
