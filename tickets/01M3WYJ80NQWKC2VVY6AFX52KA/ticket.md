+++
id = "01M3WYJ80NQWKC2VVY6AFX52KA"
title = "frob-ack: frob.lock via gob-lock, ack verb, graph why and affects, DRIFT and AFFECT rules"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0021"]
labels = ["milestone:2.0.0", "component:frob-ack"]
scope = ["crates/gob-lock/**", "crates/frob-ack/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80DWFZK0DPR4CBP0KHT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80EPBK0GGD2118X6CDT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80HVQGZY2JPE31VNQP7"

[[acceptance]]
text = "Given an acked symbol whose signature changes, when check runs, then DRIFT003 fires and frob ack clears it"
bound = true

[[acceptance]]
text = "Given a frob:doc directive pointing at a missing heading, when check runs, then DRIFT002 fires with the nearest heading"
bound = true
+++

Implement crates/gob-lock and crates/frob-ack per code-model.md sections 2 and 6 and D28. gob-lock: lock file format (TOML, sorted, one entry per symref with the three facet digests and the ack actor/date/reason), load/save/diff, product-parametric file name. frob-ack: frob.lock at the repo root; frob ack <symref|path> [--all] [--reason] records current digests through a ledger-style commit (gob-git commit_paths on the current branch, since frob.lock is code-adjacent, not ledger); DRIFT001 symbol whose doc-bound target (frob:doc) changed since ack, DRIFT002 bound doc anchor missing, DRIFT003 ack stale (sig digest changed), AFFECT001 dependent public symbol changed without its own ack; frob graph why <symref> (why a finding fires, path through the graph) and frob graph affects <symref>. Rules use the persisted findings cache keyed by graph digest. Dogfood against this repository.
