+++
id = "01M5CQ4WJJRWTQ7J9K20EWC4K9"
title = "Findings JSON FindingRecord/EditRecord file field as RelPath"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T13:13:54Z"
updated = "2026-11-09T16:39:50Z"
labels = ["no-story"]
scope = ["crates/gob-diagnostics/**", "crates/gob-path/**", "crates/frob-ledger/tests/persisted_paths.rs"]
+++

Follow-up of ~YGK8FGN: gob-diagnostics record.rs holds file as Option<String> (display path from SourceProvider); give RelPath serde in gob-path then convert and drop the persisted_paths allowlist entries.

no-story: internal engineering task in gob-diagnostics; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
