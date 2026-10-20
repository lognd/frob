+++
id = "01M418B3JG4FQ3CJGV5W87T6MG"
title = "Wire lease-aware PM013 in frob check and add the expedite/stale mdtest DSL"
type = "chore"
category = "done"
outcome = "duplicate"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T16:07:49Z"
updated = "2026-10-03T16:23:19Z"
scope = ["crates/frob-check/src/product.rs", "crates/frob-pm/tests/corpus.rs", "crates/frob-pm/tests/mdtest/pm013.md"]

[[links]]
kind = "blocked-by"
target = "01M4069TJA7YJTYSZCATV5ZYFS"
+++

found while working ~7HWFTBP: frob_pm::rules::wip::evaluate_with(ledger, WipLimits, live) is the lease-aware, lane-aware PM013 entry point, but product.rs wip_findings still calls the legacy evaluate(ledger, limit) and tests/corpus.rs cannot express class=expedite, expedite_max or stale. Both files are leased by ~TV5ZYFS (PM033). Ready patches (live_leases helper using LeaseStore::live_snapshot, corpus DSL, six pm013.md cases) were drafted in the 7HWFTBP worktree session; re-derive per docs/design/pm-enforcement.md section 6.
