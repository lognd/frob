+++
id = "01M7EX7ZFJNWWXNGFAB0R2WWDV"
title = "hunk_presence: exempt ledger commits by path rather than by heuristic"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:10:20Z"
updated = "2026-11-15T06:10:20Z"
labels = ["no-story"]

[[acceptance]]
text = "A commit touching only tickets/** is never reported as dropped (test)"
bound = false

[[acceptance]]
text = "A mixed commit still reports dropped code hunks (test)"
bound = false
+++

Source: frob-audit-meta.md M1 (hunk_presence.rs:114). Evidence: ledger-only commits can be misreported as dropped hunks. Remedy: exempt paths under the ledger dir (tickets/**) explicitly. Files: crates/frob-land/src/hunk_presence.rs.
