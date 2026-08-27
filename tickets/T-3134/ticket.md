---
id: T-3134
title: T-3121 landing-doc section still describes the post-publish land_commit record
  as an in-root commit
state: done
kind: docs
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:grep -n 'compare-and-swap' docs/modules/tickets-landing.md exit=0 sha256=ce35b16324b1
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 87ad21e8205b54a503038cf7c869f1fa1eb784ed
---
T-3126 moved `_record_land_commit` off the shared root: it now composes
its follow-up bookkeeping commit in a disposable worktree checked out at
the landing commit, folds it, and publishes it onto root's own HEAD
symref by compare-and-swap (`publish_ref_cas`) before resyncing root with
`resync_root_to_published_tip`.

docs/modules/tickets-landing.md's "What deliberately did NOT move"
section still says the opposite -- that `_record_land_commit` "makes its
own follow-up commit in root, so a small post-publish dirty window in
root remains". That statement is now false, and it is exactly the section
a reader consults to learn where a land can still dirty root.

Filed rather than fixed inside T-3126 because
docs/modules/tickets-landing.md is under a LIVE cross-worktree lease held
by in-progress T-3116, so `frob ticket scope T-3126 --add` refused it
(ScopeLeaseConflict). No doc edge was bound on the new code rather than
binding one to a section that contradicts it.

Fix: rewrite that bullet to describe the out-of-tree compose + CAS
publish, and add its post-publish failure semantics (a lost CAS leaves
the sibling's tip untouched and the record field simply absent; a blocked
resync is not a land failure, exactly as for the landing commit).
Measured numbers to cite: 8/22 untorn porcelain samples dirty before,
0/61 after.