+++
id = "01M7EXV1VFDA5AV3VTTN98XX5Q"
title = "crunk review: exact fingerprint match for signed acks"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:45Z"
updated = "2026-11-15T06:20:45Z"
idempotency_key = "crunkplan-f20c313b427c"
labels = ["no-story"]

[[acceptance]]
text = "a suffix of a listed fingerprint does not match"
bound = false
+++

Source: /home/logan/projects/frob-audit-grimble-crunk.md, finding L8.
Evidence: ends_with both ways accepts short key ids
Remedy: compare full fingerprints; long id only when %GF empty and >=16 hex
Crates/files: crates/crunk-rules/src/review.rs:108-111
Verify against HEAD first; the audit ran on a stale binary.
