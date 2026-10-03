+++
id = "01M40FXTW5FYKQWG82PD8STDJR"
title = "frob init hard-codes [tickets] ref = refs/heads/main; ticket new fails on a repository whose branch is trunk"
type = "bug"
category = "in-progress"
priority = "medium"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T09:01:08Z"
updated = "2026-10-03T09:11:40Z"
idempotency_key = "m2-rel-e2e-init-ledger-ref"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob/src/init.rs", "crates/frob/tests/init_adopt.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/frob/src/config_cmd.rs"]

[[acceptance]]
text = "Given a fresh repository whose checked-out branch is trunk, when frob init runs, then frob.toml has ref = refs/heads/trunk and frob ticket new succeeds"
bound = true

[[acceptance]]
text = "Given a repository on main, when frob init runs, then ref stays refs/heads/main"
bound = false
+++

found while working ~7R0EMJ4. Exact failure: git init -b trunk; commit; frob init writes ref = "refs/heads/main"; frob --json ticket new exits 3 with E-LEDGER-REF-MISSING 'ledger ref refs/heads/main does not exist'. Bound by crates/frob/tests/e2e_init_loop.rs init_points_the_ledger_ref_at_the_current_branch (expected-to-fail until fixed; drop its should_panic when this lands). Related: ~VA936C5 ([check] base detection).
