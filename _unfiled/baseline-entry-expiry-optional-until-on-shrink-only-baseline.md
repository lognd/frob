+++
id = "01M7EXVWZD2R6YTW0T2G6H0ETB"
title = "Baseline entry expiry: optional until= on shrink-only baseline pools"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:21:13Z"
updated = "2026-11-15T06:21:13Z"
idempotency_key = "static-research-k17"
labels = ["no-story"]

[[acceptance]]
text = "A baseline entry with an until date in the past no longer suppresses its finding"
bound = false

[[acceptance]]
text = "Entries without until behave exactly as today (shrink-only)"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 15. Verify first whether defer already covers it. Findings at HEAD: B7VH1B4 (done) added EXC016/EXC017 and until= evaluation for exceptions (frob:defer until=), and docs/design/dup.md mentions frob baseline prune; no baseline-entry until/expiry was found in docs/design or crates/frob-obligations/src. Defer expires an in-code exception, not a baseline entry, so the gap is believed real but confirm that defer cannot be applied to baselined findings. If defer covers it, close this ticket as wont-fix with that reason. Remedy: optional until on baseline entries; an expired entry stops suppressing and the finding fails the ratchet. Crates/files: baseline store (frob baseline verbs), crates/frob-obligations.
