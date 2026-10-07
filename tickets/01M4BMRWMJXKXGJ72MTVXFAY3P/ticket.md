+++
id = "01M4BMRWMJXKXGJ72MTVXFAY3P"
title = "gob-git: bulk blob read by oid so ledger walks stop resolving each path through the tickets tree"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-07T16:57:28Z"
updated = "2026-10-07T16:57:28Z"
idempotency_key = "gob-git-bulk-blob-read"
labels = ["milestone:2", "area:pm"]
scope = ["crates/gob-git/**", "crates/frob-ledger/src/**"]

[[acceptance]]
text = "Given a tree, when the bulk API lists it, then it returns each path with its blob oid in one walk and blobs are read by oid without a per-path tree lookup"
bound = false

[[acceptance]]
text = "Given this repository's ledger, when frob board runs, then reading event blobs no longer dominates (measured before and after in the done-report)"
bound = false
+++

Follow-up to ~9VT321D: after one sync and one tree walk, frob board still spends about 10.7 s of 12-21 s reading 5051 event blobs; gob_git::Repo::read_blob_at costs about 2 ms per call in a debug build because it resolves each path through the large tickets tree. Add a tree walk that returns (path, oid) and a read by oid; switch Ledger::events_many to it. The other per-ticket events loops (frob-pm cycle/velocity.rs done_facts, frob release_cmd.rs, ticket doctor_cmd.rs) can then move to events_many.
