+++
id = "01M3ZX86R5V67MT726K3X7KVWM"
title = "TICK007 reindex-not-pure: replay check"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:45Z"
updated = "2026-10-11T19:18:00Z"
idempotency_key = "m2-nav-tick005"
labels = ["milestone:2", "area:navigation", "creates:crates/frob-ledger/src/replay.rs", "creates:crates/frob/tests/ticket_replay.rs", "creates:crates/gob-mdtest/coverage-allowlist.toml", "creates:crates/gob-git/src/tag.rs", "creates:crates/gob-git/src/lib.rs", "creates:crates/frob-ledger/src/rules.rs", "creates:crates/frob-ledger/src/lib.rs", "creates:crates/frob-ledger/src/reindex.rs", "creates:crates/frob-check/src/product.rs", "creates:docs/reference/rules/TICK007.md", "creates:docs/reference/rules/README.md"]
scope = ["crates/frob-obligations/src/tick_reindex.rs", "crates/frob-ledger/src/replay.rs", "crates/frob/tests/ticket_replay.rs", "crates/gob-mdtest/coverage-allowlist.toml", "crates/gob-git/src/tag.rs", "crates/gob-git/src/lib.rs", "crates/frob-ledger/src/rules.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/src/reindex.rs", "crates/frob-check/src/product.rs", "docs/reference/rules/TICK007.md", "docs/reference/rules/README.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85X37W6QSQSJD1WYVKZG"

[[acceptance]]
text = "Given a reindex commit whose trailer names an unavailable frob version, when checked, then the result is Unresolved generator-version"
bound = true

[[acceptance]]
text = "Given a reindex commit with one hand-edited ticket body, when checked, then TICK007 fires"
bound = true
+++

Implements navigation.md section 2.2.

Replay the reindex in memory on the parent commit's tree with the frob version named in the trailer; the tree id must equal the commit's. When that version is unavailable the result is Unresolved reason generator-version.
