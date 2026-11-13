+++
id = "01M79VC7TDW5WRRPQDHQH2Y0WM"
title = "Flaky test: sync_policy doable_warns_when_offline_and_the_view_is_old sees W-SYNC-STALE instead of W-SYNC-OFFLINE under CI load"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-13T07:01:30Z"
updated = "2026-11-13T10:29:22Z"
scope = ["crates/frob/tests/it/sync_policy.rs"]

[[acceptance]]
text = "Given the clone is offline with a 2h-old view, when ticket doable runs, then W-SYNC-OFFLINE is reported even if a straggling refresh holds the lock"
bound = false
+++
