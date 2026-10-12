+++
id = "01M3ZX86ZX0SCN2FHTDBQF97FD"
title = "TICK009 misfiled-ticket with machine fix"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-11T19:53:32Z"
idempotency_key = "m2-nav-tick007"
labels = ["milestone:2", "area:navigation", "creates:crates/frob-ledger/src/misfiled.rs", "creates:crates/frob/tests/ticket_misfiled.rs", "creates:crates/gob-mdtest/coverage-allowlist.toml", "creates:crates/frob-ledger/src/rules.rs", "creates:crates/frob-ledger/src/lib.rs", "creates:crates/frob-check/src/product.rs", "creates:docs/reference/rules/TICK009.md", "creates:docs/reference/rules/README.md"]
scope = ["crates/frob-obligations/src/tick_misfiled.rs", "crates/frob-ledger/src/misfiled.rs", "crates/frob/tests/ticket_misfiled.rs", "crates/gob-mdtest/coverage-allowlist.toml", "crates/frob-ledger/src/rules.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-check/src/product.rs", "docs/reference/rules/TICK009.md", "docs/reference/rules/README.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given all files at computed paths, when checked, then it does not fire"
bound = true

[[acceptance]]
text = "Given a ticket file at a stale path, when checked, then TICK009 fires and the fix is `frob ticket reindex`"
bound = true
+++

Implements navigation.md section 2.2.

On the tip of the branch every ticket file is at its computed path; the fix is frob ticket reindex.
