## Done report

### Verified mechanism (not just the coordinator's relay)

Confirmed by reading the actual code, not assumed:

- `"requeue"` was classified `LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED`
  in `LEDGER_VERB_STRATEGY` (src/frob/app/ticket_runner/_ledger_mirror.py).
  That table is what `_auto_commit_ledger_after_dispatch`
  (src/frob/app/ticket_runner/__init__.py) gates
  `mirror_ledger_change_to_primary` on: UNMIRRORED verbs still call
  `mirror_ledger_change_to_primary`, but `_mirror_target` short-circuits
  to `None` unless `command in MIRRORED_LEDGER_VERBS` -- so the local
  commit happened, and the mirror step was reached, but did nothing.
- The GENERIC_COMMIT_UNMIRRORED rationale ("land already carries this
  atomically with the code it describes") is TRUE for close/drop/fail/
  done-report, and FALSE for requeue: requeuing means the ticket's
  worktree work is explicitly NOT going to land. There is no future
  land event for any mechanism to piggyback the ledger state onto.
- Confirmed T-2785's `_refuse_write_if_land_in_progress`-style guard
  DOES cover this path already (`_resolve_mirror_primary` calls
  `refuse_if_land_in_progress` before attempting to mirror) -- the gap
  was purely the missing table entry, not a missing land-guard.
- Confirmed `frob.tickets._unlanded`'s finished-work detector does NOT
  catch a requeue commit sitting on a worktree branch: it looks for a
  done-report or `state: done/dropped`, never a ticket going BACKWARD
  to `queued` -- so a requeuing worktree reads as ordinary "committed,
  clean, no finished work here" and is a normal sweep candidate once
  its clean working tree makes it look abandoned-but-safe.

### T-2785 guard scope confirmed

`_resolve_mirror_primary` (shared by both `mirror_ledger_change_to_primary`
and `mirror_promote_to_primary`) already refuses and logs loudly
(`_log_mirror_unavailable`) if a land is in progress -- this is the
generic path every `GENERIC_COMMIT_MIRRORED` verb already goes through,
and `requeue` now inherits it for free by joining that strategy. No
separate land-guard work was needed.

### Fix

Reclassified `"requeue"` from `GENERIC_COMMIT_UNMIRRORED` to
`GENERIC_COMMIT_MIRRORED` in `LEDGER_VERB_STRATEGY`
(src/frob/app/ticket_runner/_ledger_mirror.py). This is the entire code
change: `_auto_commit_ledger_after_dispatch`'s existing unconditional
call to `mirror_ledger_change_to_primary` now actually mirrors requeue's
ledger write, synchronously, inside the same `frob ticket requeue`
invocation, before the command returns -- well before any worktree-sweep
decision is ever made. Updated `LedgerWriteStrategy`'s own docstring
(both the GENERIC_COMMIT_UNMIRRORED and GENERIC_COMMIT_MIRRORED
sections) to explain why requeue moved, and appended a new subsection to
docs/modules/tickets-lifecycle.md under "One verb table, not two sets"
documenting the measured incident, the mechanism, and the fix.

### Required shape addressed

Per the ticket's explicit choice of options ("verify the mirror reached
primary before reporting success, OR report LOCAL-ONLY explicitly"): this
repo's established precedent for every other GENERIC_COMMIT_MIRRORED verb
is the second option -- `_log_mirror_unavailable` logs a loud ERROR naming
the exact recovery command whenever the primary is unreachable (a land in
flight), while the verb's own local commit still reports success (the
local write really did succeed). `requeue` now gets this exact same
treatment, consistent with `scope`/`block`/`unblock`, rather than a
bespoke behavior. No exit-code change to `requeue` itself; the fix is
that the SUCCESS PATH now actually reaches main, which is what makes the
existing "local commit succeeded, report success" behavior honest.

### Positive controls (both directions), as required by the ticket

- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_requeue_edit_from_worktree_is_visible_on_primary`
  -- requeue issued from a worktree reaches the primary checkout's
  committed tree immediately (a distinguishing marker proves the copy
  really happened, not just that both ends coincidentally already read
  "queued").
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope::test_requeue_running_in_the_primary_checkout_is_a_no_op`
  -- requeue issued from the primary checkout is unchanged: no invented
  commit, clean working tree after.

### Genuine repro, not confirmatory-only (T-1929 self-check run before designating)

Per BUG002/T-1929 discipline: committed the repro test ALONE first
(commit 42affe3a3049fec29da582ab6088f89887bcc05f, unfixed source still
present), ran it directly -- it genuinely FAILED
(`AssertionError: assert 'requeue' in frozenset(...)`), confirming this
is not a confirmatory-only test. Then committed the fix
(16bceabb5) and re-ran the full file: 22 passed, 0 failed.
`frob ticket evidence --check-repro`/`--designate-repro` against that
parent commit both report `FAILED_AT_PARENT` -- a real repro, not
`PASSED_AT_PARENT`/`NO_VERDICT`.

### Evidence

- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_requeue_edit_from_worktree_is_visible_on_primary
  (designated repro, FAILED_AT_PARENT at 42affe3a3)
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope::test_requeue_running_in_the_primary_checkout_is_a_no_op

### Filed

None -- no out-of-scope discoveries. (Note: the ticket body's own
"Consider also whether an empty/no-scope worktree should be eligible for
eager cleanup at all" question turned out unnecessary to answer
separately -- fixing the mirror timing removes the race entirely, since
main is updated synchronously inside the `requeue` call itself, before
any later sweep decision can matter.)

### Gates

- Full test file: 22 passed, 0 failed
  (tests/unit/test_ticket_runner_ledger_mirror.py).
- `frob check --only static`: no new findings on touched files (frob-arch/
  frob-cycle/exports counts unchanged from pre-change baseline).
- `frob check --only gates-fast --ticket T-2840`: gate:SCOPE clean (0
  errors); the 3 gate:COV warnings touching _ledger_mirror.py (COV007,
  frob:doc on private symbols) are PRE-EXISTING, not from this diff (same
  private symbols/anchors this diff did not touch). gate:DRIFT/TEST/TICK/
  REF/REG/PRE failures are the repo-wide pre-existing red main (T-2846
  fallout, T-2855 in progress) per dispatch brief -- not attributable to
  this diff, confirmed by cross-checking the diagnostic file paths.

### Changed
```
 docs/modules/tickets-lifecycle.md              | 44 ++++++++++++++++++++
 src/frob/app/ticket_runner/_ledger_mirror.py   | 35 +++++++++++++---
 tests/unit/test_ticket_runner_ledger_mirror.py | 56 ++++++++++++++++++++++++++
 tickets/T-2840/ticket.md                       | 22 +++++++++-
 4 files changed, 150 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_requeue_edit_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope::test_requeue_running_in_the_primary_checkout_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 62 error(s), 529 warning(s), 794 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC006@docs/modules/graph.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@docs/modules/tickets-landing.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DUP001@tests/unit/test_ticket_runner_ledger_mirror.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2840/src/frob/gates/_mutation_evidence.py, F822@/home/logan/projects/frob/.claude/worktrees/t-2840/src/frob/gates/_bug_repro.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2840, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
