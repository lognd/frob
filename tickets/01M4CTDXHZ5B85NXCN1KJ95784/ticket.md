+++
id = "01M4CTDXHZ5B85NXCN1KJ95784"
title = "land ratchet: key the base-check cache by the code tree without tickets/ so ledger commits stop forcing a full re-check (audit M5)"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:34Z"
updated = "2026-10-08T03:55:34Z"
scope = ["changelog.d/**", "crates/frob-land/**"]

[[acceptance]]
text = "Given two base commits that differ only under tickets/, when land checks the base, then the second check is a cache hit (test counts the check runs)"
bound = false

[[acceptance]]
text = "Given a base commit that changes a code file, when land checks the base, then the cache misses"
bound = false
+++

notes/review/audit-2026-10-07.md M5, frob-land/src/ratchet.rs 91-121. The cache key is the base commit oid; every ticket write is a new commit, so it never hits and each land re-checks the base (about 7 min). Key on the tree oid of the code paths (the base tree with the ledger directory removed) plus config and binary digests.
