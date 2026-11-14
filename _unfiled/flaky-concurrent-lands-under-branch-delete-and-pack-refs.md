+++
id = "01M7C1S13G3QCMFRW8V7HZCE06"
title = "Flaky: concurrent_lands_under_branch_delete_and_pack_refs_churn fails E-LEDGER-REF-MISSING for refs/heads/main"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-14T03:31:49Z"
updated = "2026-11-14T03:31:49Z"
scope = ["crates/frob-land/**", "crates/frob-ledger/**"]

[[acceptance]]
text = "Given concurrent lands under branch-delete and pack-refs churn, when a ref is momentarily repacked, then no land fails with E-LEDGER-REF-MISSING and the test passes 20 runs in a row"
bound = false
+++

CI run 43548987012 Linux job 132306916495, land.rs:2008 round 8: 'land a failed uncleanly: E-LEDGER-REF-MISSING: ledger ref refs/heads/main does not exist'. Decide whether the ref read races pack-refs (product bug: retry or read via packed refs) or the churn helper deletes the base (test bug).
