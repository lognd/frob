+++
id = "01M68PYYN7A5TCY068A3K6V7CW"
title = "Write precision-history.json atomically (temp file plus rename)"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T10:09:24Z"
updated = "2026-10-31T10:09:24Z"
scope = ["crates/gob-rules/src/precision_history.rs"]

[[acceptance]]
text = "PrecisionHistory::save writes via gob_fs::write_atomic so a crash mid-write cannot truncate precision-history.json"
bound = false
+++

Found while working AA9C2BY: save uses std::fs::write; frob dismiss and check runs can also lose updates since there is no lock (separate concern).
