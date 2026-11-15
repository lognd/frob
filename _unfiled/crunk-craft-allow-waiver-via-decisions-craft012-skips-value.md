+++
id = "01M7EXTH62J0RFWT009012D0TB"
title = "crunk CRAFT: allow waiver via [decisions]; CRAFT012 skips value kinds with no token type"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:28Z"
updated = "2026-11-15T06:20:28Z"
idempotency_key = "crunkplan-618c5eb3cbb1"
labels = ["no-story"]

[[acceptance]]
text = "a [decisions] waiver silences a CRAFT finding"
bound = false

[[acceptance]]
text = "CRAFT012 ignores kinds with no token type"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding L6.
Evidence: CRAFT rules cannot be waived through [decisions]
Remedy: wire CRAFT into decisions; exclude untokenised value kinds from CRAFT012
Crates/files: crates/crunk-rules craft
Verify against HEAD first; the audit ran on a stale binary.
