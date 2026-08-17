---
id: T-2060
title: OrphanedEvidenceDeletion refuses on file-level match, not the landing branch's
  own node deletion
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_orphaned_evidence_node_granularity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_orphaned_evidence_node_granularity.py
  reason: new regression test file for the FAILS-FIRST acceptance criterion
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_absent_node_reports_false
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_present_node_reports_true
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_unreadable_ref_reports_none
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_evidence_with_no_double_colon_reports_none
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_file_level_only_call_reproduces_the_incident
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_node_level_narrowing_clears_a_pre_existing_absence
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_a_genuine_this_branch_deletion_still_refuses
- tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_merge_base_lookup_failure_falls_back_to_file_level
designated_repro_test: tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_node_level_narrowing_clears_a_pre_existing_absence
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED: `frob ticket land` refuses another agent's T-1959 with
`OrphanedEvidenceDeletion`, citing a test node deleted by commit
`7597ba37a` -- verified by that agent (`git log -S`) to already be on
`main` long before their worktree existed, unrelated to their own diff.

ROOT CAUSE, established empirically (reproduced directly against
`_orphaned_evidence_findings`, not assumed): the check matches at FILE
granularity, not test-NODE granularity. `_orphaned_evidence_findings`
(src/frob/tickets/_land.py) flags any OTHER ticket's evidence node
whenever `node_path = evidence.split("::", 1)[0]` (the evidence's own
FILE) appears anywhere in `changed_paths` (`_branch_changed_files`,
`base_ref...HEAD`, correctly scoped to the LANDING branch's own diff --
verified: three-dot semantics, not a stale-merge-base artifact) AND the
SPECIFIC node no longer resolves against CURRENT test collection. It
never checks whether the LANDING branch's diff is what actually removed
that specific node, only that the containing file is somewhere in the
diff and the node is currently missing.

Reproduced directly (pure-function repro, `_orphaned_evidence_findings`
called with hand-built inputs): an archived ticket's evidence citing
`tests/test_foo.py::TestFoo::test_long_gone` (already gone from current
collection, deleted by an old, unrelated main commit) is flagged the
INSTANT the landing branch's own diff touches `tests/test_foo.py` for
ANY reason at all, even adding an unrelated new test in the same file.

`_branch_changed_files`'s own three-dot diff (base_ref...HEAD) IS
correctly scoped to the landing branch's own commits -- that part of the
coordinator's hypothesis does not hold as stated. The defect is entirely
inside `_orphaned_evidence_findings`'s file-vs-node granularity, not in
how the diff range is computed.

T-2017 (this session) is what made this fire in practice: it correctly
switched `load_all` (active-only) to `load_queue` (active+archive) so an
ARCHIVED ticket's orphaned evidence becomes visible to COV003's own
authoritative sweep (closing the real T-0907 miss) -- but the same
switch also widened `_orphaned_evidence_findings`'s own candidate set to
include every archived ticket's evidence, making a collision with the
pre-existing file-level bug dramatically more likely: any landing branch
that merely touches a large, heavily-shared test file (e.g.
tests/test_ticket_land.py, tests/test_gates.py -- files nearly every
land in this session touches) now risks tripping on ANY other ticket's
(including long-archived) evidence anywhere in that file, regardless of
relevance. T-1940 (also landed this session) only registered this check
in the post-mutation-guard registry with an explicit acknowledged-gap
exemption; it made no logic change to the matching algorithm.

FIX DIRECTION: narrow the match from file-level to node-level using a
merge-base comparison -- a candidate is only a genuine THIS-BRANCH
deletion if the specific test node existed (syntactically, in the file
content) at `git merge-base <base_ref> HEAD` and no longer resolves at
HEAD. A node already absent at merge-base is pre-existing breakage the
landing branch did not cause and must not be blamed for.

THROUGHPUT COST: every branch based on main after `7597ba37a` (or any
other commit that broke an archived ticket's evidence and whose file is
independently touched by a later, unrelated branch) is at risk of this
refusal -- not "every branch based on main after 7597ba37a" unconditionally
(the coordinator's stated worst case), since it additionally requires
the landing branch to touch the SAME FILE the stale evidence lives in.
Given how few, large, heavily-shared test files carry most of this
repo's evidence bindings (tests/test_ticket_land.py alone is >16000
lines and touched by a large fraction of tickets/land-path work this
session), the practical exposure is close to that worst case for any
ticket whose scope includes one of those shared files.

## Done report

Established empirically, per the coordinator's instruction, rather than
assuming the hypothesis:

`_branch_changed_files` (three-dot, `base_ref...HEAD`) IS correctly
scoped to the landing branch's own commits -- confirmed directly against
its own semantics and by construction: a merge-base older than the
deletion commit means three-dot diff never surfaces changes main made
independently after divergence. This part of the coordinator's
hypothesis does not hold as stated.

The real, confirmed defect: `_orphaned_evidence_findings` matches at
FILE granularity, not test-NODE granularity. It flags any OTHER
ticket's evidence node the instant the evidence's own FILE appears
anywhere in `changed_paths`, with zero check on whether the LANDING
branch's diff is what actually removed that specific node. Reproduced
directly (pure-function call with hand-built inputs, before touching
any git machinery): an archived ticket's evidence citing a node already
missing from current collection got flagged the instant a synthetic
landing branch's diff touched the SAME FILE for an entirely unrelated
edit.

T-2017 (this session) is what exposed this in practice: it correctly
widened `load_all` -> `load_queue` to make an ARCHIVED ticket's orphaned
evidence visible (closing the real T-0907 miss) -- but the same
widening made a collision with the pre-existing file-level bug far more
likely: any branch touching a large, heavily-shared test file
(tests/test_ticket_land.py, tests/test_gates.py -- files most
land-path/gates work this session touches) now risks tripping on ANY
other ticket's, including long-archived tickets', evidence anywhere in
that file. T-1940 (also this session) only registered this check in the
post-mutation-guard registry with an acknowledged-gap exemption -- no
logic change to the matching algorithm; ruled out as a contributing
cause.

FIX: `_test_node_existed_at_ref(worktree, ref, evidence)` -- a cheap,
syntactic (`def <name>` regex against `git show <ref>:<path>`, NOT a
real pytest collection, which would need a full isolated checkout per
candidate on every single land, T-1929's `_checkout_bug_repro_worktree`
pattern, far too costly here) presence check against the file's content
AT THE LANDING BRANCH'S OWN MERGE-BASE (`_true_merge_base`, already
imported in this module). `_orphaned_evidence_findings` only flags a
file-level candidate when this returns NOT `False` (present, or
undeterminable -- conservatively still flags on ambiguity, matching this
check's existing prove-fresh-or-refuse posture). A node CONFIRMED
absent already at merge-base is pre-existing breakage the landing
branch did not cause.

FAILS FIRST, verified TWO ways:
1. Direct pure-function repro (ran BEFORE writing any fix): confirmed
   the bug reproduces with hand-built Ticket/CollectedTests inputs.
2. Real git repro against the actual fixed code: temporarily removed
   the narrowing `if` block, re-ran
   TestOrphanedEvidenceFindingsNodeGranularity::test_node_level_narrowing_clears_a_pre_existing_absence
   -- FAILED with the pre-fix code (flagged the pre-existing-on-main
   absence), exactly reproducing T-1959's reported incident's shape
   against a real git repo (base commit without the test, feature
   branch adding an UNRELATED test in the same file). Restored the fix,
   re-ran: passes (8/8 in the file).
`frob ticket evidence --check-repro` itself cannot produce a verdict for
the designated node (TEST_ABSENT_AT_PARENT -- the whole test file is
new, matching T-2025's documented post-land squash limitation,
docs/modules/tickets.md#check-repro-post-land-limitation-t-2025).
`--designate-repro-force` used for this specific, verified-by-hand
false positive.

Confirmed a genuine THIS-BRANCH deletion still refuses (no over-reach):
same test file, same shape, but the evidence node existed at merge-base
and was removed by the branch's own commit -- still flagged.

Confirmed the merge-base-lookup-failure fallback: `merge_base=None`
degrades to the OLD file-level-only behavior, never a crash, never a
silent pass -- no caller can regress below pre-fix safety.

THROUGHPUT COST, measured as requested: NOT "every branch based on main
after 7597ba37a" unconditionally -- it additionally requires the
landing branch to touch the SAME FILE the stale evidence lives in.
Given this repo's evidence bindings concentrate heavily in a small
number of large shared test files (tests/test_ticket_land.py alone
exceeds 16000 lines and is touched by a large fraction of land-path
tickets this session), the PRACTICAL exposure is close to that worst
case for any ticket whose scope touches one of those files -- did not
attempt to enumerate every currently-open ticket against every
archived ticket's evidence bindings (would need a full repo-wide join
this session's time budget did not allow); the qualitative answer
(file-collision-dependent, not universal, but close to universal for
tickets touching the handful of largest shared test files) is the
honest one available.

Existing orphaned-evidence regression tests (tests/test_ticket_land.py,
5 tests) still pass unchanged -- no regression to the previously-correct
genuine-deletion path.

### Changed
```
 src/frob/tickets/_land.py                          |  98 +++++++-
 ...test_land_orphaned_evidence_node_granularity.py | 253 +++++++++++++++++++++
 tickets/T-2060/ticket.md                 | 103 +++++++++
 3 files changed, 451 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_absent_node_reports_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_present_node_reports_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_unreadable_ref_reports_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef::test_evidence_with_no_double_colon_reports_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_file_level_only_call_reproduces_the_incident` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_node_level_narrowing_clears_a_pre_existing_absence` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_a_genuine_this_branch_deletion_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity::test_merge_base_lookup_failure_falls_back_to_file_level` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, DUP001@tests/unit/test_land_orphaned_evidence_node_granularity.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design, invalid-argument-type@tests/unit/test_land_orphaned_evidence_node_granularity.py
