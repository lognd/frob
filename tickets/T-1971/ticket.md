---
id: T-1971
title: migrate all frob-wired sibling repos off v1 ledger before deleting v1 splice
  machinery
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- N/A -- coordinator/cross-repo tracking
- no code in this repo
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed while working T-1552 so its real blocker has a concrete id.

T-1552 assumed "main is migrated" (this repo's own tickets.md/
tickets-archive.md) was the whole precondition for deleting the v1
splice machinery (splice_ledger, _land_merge.py, _land_merge_zones.py,
the .gitattributes merge-driver lines, the merge-driver CLI verb). That
half is true (T-1631, done).

But splice_ledger and its call sites (_land_squash.py's
_squash_and_splice_ledger vs _squash_and_splice_ledger_v2 dispatch on
_store_mode(root), _land_git_ops.py, _land_cmd.py's merge-driver
entry point) are generic library code, dispatched per invocation ROOT,
not hardcoded to this repo. Checked all sibling repos this frob install
is wired into: aprog-private, aprog-public, feldspar, graphite, lithos,
logand.app, lograder, typani are ALL still on the v1 tickets.md monofile
(none have run `frob ticket migrate --to v2` against their own ledger).
Only frob's own repo has migrated.

Deleting the v1 splice machinery now would break `frob ticket land` /
`frob ticket merge-driver` for every one of those 8 repos on their next
concurrent-worktree ledger conflict.

Needed before T-1552 can safely proceed: migrate each of the 8 sibling
repos to ledger v2 (same recipe T-1631 used: `frob ticket migrate --to
v2` in a quiet window per repo, verify count+content), THEN observe the
LEDGERV1001 deprecation window, THEN delete. T-1552's own scope list is
also incomplete for its stated acceptance criterion -- it omits
_land_squash.py, _land_git_ops.py, and _land_cmd.py, which hold the
actual v1/v2 branch dispatch and the merge-driver CLI verb; "frob check
reports zero references" cannot be reached without touching those too.
