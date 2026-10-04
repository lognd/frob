+++
id = "01M43H799QN5Z31VGH57TD70T6"
title = "Repo-group cache replays a failed evaluation after the ledger is repaired"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T13:21:30Z"
updated = "2026-10-04T13:21:30Z"
scope = ["crates/gob-check/src/**"]
+++

found while working ~A6C2R1C: repo group results are cached by inputs digest (ledger tip); an evaluation-failed required Unresolved is stored and replayed for the same tip after the index is repaired. Evaluation failures must not be cached.
