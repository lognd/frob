+++
id = "01M3Z7N2Z72XPNDSRHA470ARGM"
title = "frob check --ticket diffs two-dot against the base and flags ledger commits as SCOPE001"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:17:19Z"
updated = "2026-10-02T21:44:35Z"
idempotency_key = "m2-scope-diff"
labels = ["milestone:2"]
scope = ["crates/frob-check/**", "crates/frob-lease/**"]

[[acceptance]]
text = "Given a ticket branch whose base has advanced with ledger-only commits, when frob check --ticket runs, then no SCOPE001 fires for files the branch did not change"
bound = false
+++

check --ticket computes the ticket diff as base..HEAD, so once experimental moves ahead (ledger-only commits from other tickets' evidence and starts) those files appear in the ticket's diff and SCOPE001 fires on tickets/** the branch never touched. Use the merge-base (three-dot semantics: diff from merge_base(base, HEAD) to HEAD) through gob-git merge_base and diff_names, and exempt the ticket's own ledger directory and the ledger ref's files written by frob itself. Found by ticket 01M3Z712AFAG3GCEAZ66KPBWD1.
