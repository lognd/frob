+++
id = "01M7X35VPCNR2WS06MG6J290GY"
title = "Audit 2026-11-20 correctness batch: land lock liveness, post-commit errors, CAS give-up, unreadable reports, merge driver"
type = "bug"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-20T18:23:24Z"
updated = "2026-11-20T23:06:02Z"
scope = ["crates/frob-land/**", "crates/frob-ledger/**"]

[[acceptance]]
text = "Given a lock holder with a live child on a non-Linux platform, when judged, then it is busy and never stolen; given an after_commit failure, then the call reports the applied commit with a warning and does not return Err"
bound = false

[[acceptance]]
text = "Given three lost CAS attempts, when reconcile_with gives up, then it returns a contention error; given an unreadable test report or merge-driver ours file, then the error is surfaced and not read as empty; given FROB_LAND_STALL_SECS at u64 max, then there is no panic"
bound = true
+++

Findings: frob-land lock.rs:462,521,586; frob-ledger ledger.rs:1124,1227,1295; frob-evidence provider.rs:720,1014,1593,2057 unwrap_or_default on read_to_string; merge.rs:165,185 non-atomic write and masked read; lock.rs:463 Duration*2 overflow. Also crunk-spec research.rs Date::parse accepts 2026-02-31 and a BOM breaks front matter, gob-directives scan.rs NUL padding in continued directives (confirm with a test first).
