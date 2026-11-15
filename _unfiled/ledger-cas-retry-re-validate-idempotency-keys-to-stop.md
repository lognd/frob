+++
id = "01M7EX80MVCH08V6ENY70A6DN3"
title = "ledger CAS retry: re-validate idempotency keys to stop duplicate tickets"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:21Z"
updated = "2026-11-15T06:10:21Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md M4. Evidence: crates/frob-ledger/src/ops.rs:465-472 and crates/gob-git/src/ledger.rs:209-225; on a CAS conflict the retry reapplies the op without re-checking its idempotency key against the new tip. Remedy: re-run the idempotency lookup after each refetch. Files: those two files.
