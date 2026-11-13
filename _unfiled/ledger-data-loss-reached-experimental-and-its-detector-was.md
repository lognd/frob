+++
id = "01M7AV6DFBVMPWMR9KED4YR4SJ"
title = "ledger data loss reached experimental and its detector was silenced by deleting refs"
type = "incident"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-11-13T16:17:34Z"
updated = "2026-11-13T16:17:34Z"
labels = ["no-story"]
scope = ["crates/frob-ledger/**"]

[[acceptance]]
text = "Deleting refs cannot silence the loss detector; test proves it."
bound = false
+++

H3: restore detection that cannot be defeated by deleting references; see audit section H3 for the sequence. Source: frob-audit-meta.md (Opus audit).
