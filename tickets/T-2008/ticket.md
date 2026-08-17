---
id: T-2008
title: 'post-land sweep regression from T-1638: 1 new (rule, file) identit(ies) (SELFAUDIT001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1638 at commit d1126ede9901b7d141303cd98f842b8c0fb69c85 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- SELFAUDIT001  design

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-10: Re-measured before implementing, per standing guidance that sweep-filed tickets are often already-fixed (T-2000/T-1998 precedent). frob check --only sys against current main reports 0 errors/0 warnings for SELFAUDIT001 on design -- finding does not reproduce. Cross-checked via frob verify explain SELFAUDIT001:design (T-1690/T-2018 attribution tool): returned queue-empty, consistent with no live finding to attribute. Likely closed by T-2001's SYS111 Tier-A auto-fix landing after this sweep ticket was filed. Note for T-2018: the explain command's queue-empty error does not distinguish finding-resolved from other empty-queue causes, but was usable enough to confirm absence here.
