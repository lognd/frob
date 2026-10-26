+++
id = "01M5WEGKMRHCT3G66EFEK0YNZX"
title = "CI: refresh::fresh_probe_reports_age_zero_and_no_warnings sees base_sync diverged (W-SYNC-DIVERGED) on ubuntu nextest"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-26T15:50:52Z"
updated = "2026-10-26T15:50:59Z"
scope = ["crates/frob/tests/it/refresh.rs", "crates/frob/src/refresh_cmd.rs"]

[[acceptance]]
text = "The test passes deterministically on CI (fixture no longer diverges, or the divergence report is corrected) with root cause explained"
bound = false
+++

Run on bd2db3cfa9 ubuntu nextest: refresh.rs:215 warnings len 1 vs 0; data.base_sync=diverged, W-SYNC-DIVERGED. Passes locally. Suspect the clone_with_origin fixture depends on default branch name or git config, or a race with the ledger branch.
