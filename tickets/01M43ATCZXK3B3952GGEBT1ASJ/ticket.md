+++
id = "01M43ATCZXK3B3952GGEBT1ASJ"
title = "crunk query, map and explain verbs: crunk-query crate"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:36Z"
updated = "2026-10-04T11:29:36Z"
idempotency_key = "crunk-plan-qry"
labels = ["area:crunk"]
scope = ["crates/crunk-query/**", "crates/crunk/src/query.rs", "crates/crunk/src/map.rs", "crates/crunk/src/explain.rs", "crates/crunk/tests/query*.rs", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43ARZH9F9MCPJCKXM635E0X"

[[links]]
kind = "blocked-by"
target = "01M43ATCF5GGK59S96K1ZF0G9C"

[[acceptance]]
text = "Given the corpus, when each query runs with --json, then results equal the Python output"
bound = false

[[acceptance]]
text = "Given `explain unknown-token`, when run, then the exit is 2 and close matches are named"
bound = false

[[acceptance]]
text = "Given `query violations`, when violations exist, then the exit is still 0"
bound = false
+++

Port query/ (1037 LOC): find (exact > prefix > substring, then use count), component, dupes (threshold 0.6), unused, uses, color, violations (never exits 1), plus `map` inventory and `explain NAME` (exit 2 on unknown, close matches; adds a did-you-mean the Python lacks). Port tests/unit/test_query.py, test_report_query.py, e2e 09, 16, INT-10.
