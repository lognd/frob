+++
id = "01M68PYYN7A5TCY068A3K6V7CW"
title = "Write precision-history.json atomically (temp file plus rename)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T10:09:24Z"
updated = "2026-10-31T11:17:20Z"
scope = ["crates/gob-rules/src/precision_history.rs", "crates/gob-rules/Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "PrecisionHistory::save writes via gob_fs::write_atomic so a crash mid-write cannot truncate precision-history.json"
bound = true
+++

Found while working AA9C2BY: save uses std::fs::write; frob dismiss and check runs can also lose updates since there is no lock (separate concern).
