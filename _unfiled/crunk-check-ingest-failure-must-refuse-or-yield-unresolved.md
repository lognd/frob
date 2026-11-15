+++
id = "01M7EXTYA7ESJ364WAPZCDMJZG"
title = "crunk check: ingest failure must refuse or yield Unresolved, never inapplicable"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:41Z"
updated = "2026-11-15T06:20:41Z"
idempotency_key = "crunkplan-f248823e99e9"
labels = ["no-story"]

[[acceptance]]
text = "css_root set to a file fails or yields Unresolved, exit non-zero (test)"
bound = false
+++

Source: /home/logan/projects/frob-audit-grimble-crunk.md, finding M1.
Evidence: css_root pointing at a file makes COLOR/CONTRAST/SPACE inapplicable and check exits 0
Remedy: refuse with CheckError::Config or return a required Unresolved for must_measure rules
Crates/files: crates/crunk-check/src/product.rs:169-190, crates/crunk-rules/src/host.rs:92-100
Verify against HEAD first; the audit ran on a stale binary.
