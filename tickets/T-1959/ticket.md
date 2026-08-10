---
id: T-1959
title: 'Dead-by-constant-branch: close the remaining 9/23 misses left by T-1881 (multi-hop,
  boolean-composition, syntactic dead-caller)'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_dead_symbols.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
FOLLOW-UP to T-1881 (landed 969eaeca0622), which took dead-by-constant-
branch detection from 0/23 to 14/23 against a controlled denominator
(same tree, same commit `bdb39bde3`, only the detector code differing).

THIS TICKET EXISTS BECAUSE THE RESIDUE HAD NO QUEUE ENTRY. T-1881's 9
remaining misses are characterized carefully in
`tickets/T-1881/evidence/fix-measurement.md` and in that ticket's own
acceptance criterion [2]. That is a genuinely good record -- but T-1881
is DONE and archives, and neither an evidence file nor a closed ticket's
acceptance criterion is read by `frob ticket doable`. Catalogued is not
enforced: work that lives only in a done ticket's prose is invisible to
every queue view and gets silently dropped. The measurement stays where
it is; this ticket is the queue entry that points at it.

THE REMAINING 9, in three distinct classes (from that evidence file):

1. MULTI-HOP PROPAGATION GAP -- `_render_ledger`, `splice_ledger`.
   Their own direct call sites fold correctly; liveness depends on an
   upstream hop the bounded fixed point (`_MAX_TRANSITIVE_ROUNDS`) does
   not resolve, incl. a producer missed due to a shadowing import alias.

2. BOOLEAN-COMPOSITION HOP -- `_squash_and_splice_ledger`. Same folded-
   ternary shape as a case that DOES work, but its callers are reached
   through an intermediate `and`/`or` composition (`v2_mode and not
   force_v1`) that single-assignment-hop tracking does not carry. T-1881
   explicitly bounded itself to one hop, so this is a scope cut, not a
   defect in what shipped.

3. SEPARATE SYNTACTIC DEFECT -- `_require_merge_driver_args`,
   `_archived_ids_for_merge_driver`. DEAD001's call-graph walk does not
   transitively propagate dead-CALLER status past one hop for the
   ORDINARY syntactic-deletion case. This has nothing to do with constant
   folding and is the most independently valuable of the three; T-1881
   flagged it and left it open deliberately, with a regression test
   confirming it is still open.

Class 3 is the recommended starting point: it is orthogonal to the
constant-folding machinery, so it can be fixed without disturbing the
14/23 that now work.

DO NOT FIX IT THIS WAY: do not chase the ratio by loosening detection.
T-1881 verified no new findings on the live tree (0 errors before and
after) and hand-checked the extra findings it surfaced. A detector that
reports LIVE code as dead is far worse than one that misses dead code --
acting on a false positive deletes working code. Every added detection
must be provable; if a case cannot be proven, leave it a MISS and say so.

Also do not re-derive the baseline. Reuse T-1881's harness and the SAME
denominator (23 symbols at `bdb39bde3`, see
`tickets/T-1881/evidence/denominator.md`) so the ratio stays comparable.
A new denominator makes the numbers incomparable and hides regressions.

ACCEPTANCE: report a new detected/23 ratio against that same denominator,
with each still-missing symbol individually characterized (no collapsing
into name-groups). Confirm `frob check --only dead_symbols` stays at 0
errors on the live tree. First test must fail before the fix.
