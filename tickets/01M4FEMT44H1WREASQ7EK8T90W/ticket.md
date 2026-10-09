+++
id = "01M4FEMT44H1WREASQ7EK8T90W"
title = "TICK002 under ref_mode = branch resolves ticket refs against main instead of the current branch's ledger"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T04:27:15Z"
updated = "2026-10-09T18:03:27Z"
labels = ["adoption:hullbreach", "creates:changelog.d/01M4FEMT44H1WREASQ7EK8T90W*"]
scope = ["crates/frob-ledger/tests/ledger.rs", "changelog.d/01M4FEMT44H1WREASQ7EK8T90W*", "crates/frob-check/src/scope.rs"]

[[acceptance]]
text = "Given ref_mode = branch and a ticket created on the current branch, when a frob:ticket directive names it, then TICK resolves it from the branch ledger (base plus branch) with no TICK002; a ticket that exists on neither still fires TICK002"
bound = false
+++

Hullbreach game repro: with ref_mode branch the ledger commits live on the PR branch until merge, so TICK002 'not present on main' fires on every new ticket's directive.
