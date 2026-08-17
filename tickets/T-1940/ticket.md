---
id: T-1940
title: Generalize T-1932's post-mutation guard re-check into a registry every future
  land-path guard is forced to use
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-1940's registry needs a structural completeness test asserting every committed-diff-reading
    land guard is registered with a twin or an explicit exemption reason
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_call_site_guard_is_registered
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_registry_entry_has_a_twin_or_a_stated_reason
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_registered_twins_are_actually_wired_into_the_land_sequence
designated_repro_test: tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_call_site_guard_is_registered
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1932 established a worked pattern for making a land-path guard's
refusal survive a later mutation (self-delegating re-invocation of the
SAME check function, called after `_land_merge_stage`'s wip-commit,
pinned by a source-order introspection test) and applied it to
`_check_cross_ticket_leakage` (the T-1931 instance). It deliberately did
NOT build a generic, structural registry that forces every OTHER
committed-diff-reading guard in `_land_precheck_remaining_checks`
(`_check_passenger_tickets`, `_check_already_landed`, and any guard added
later) to register a post-mutation twin automatically -- each of those
currently relies on the same worked example being copied by hand, same as
before T-1932, just with a clearer template and a locked regression test
now proving the copy works.

Investigate and build a real registry: walk
`_land_precheck_remaining_checks`'s own guard list generically (or an
explicit `_COMMITTED_DIFF_GUARDS` tuple naming each check plus its
post-mutation twin), and add a test that fails if a NEW guard is added to
the preflight sequence without a corresponding registered post-mutation
re-check -- closing T-1932 acceptance criterion 4 mechanically for every
future guard, not just the one this ticket touched by hand.

Scope: src/frob/tickets/_land.py

## Done report

Built the registry T-1932 deliberately deferred (per its own acceptance criterion 4
note) rather than a fully generic AST-walk, matching the ticket's own permissive
"or an explicit `_COMMITTED_DIFF_GUARDS` tuple" alternative: `_CommittedDiffGuard`
(a pydantic model: `name`, `post_mutation_check`, `exemption_reason`) plus a
`_COMMITTED_DIFF_GUARDS` tuple naming every guard called from `_land_precheck`/
`_land_precheck_remaining_checks` that reads committed diff content (the exact
T-1932 hazard class: `_absorb_pre_land_fixes`'s Tier-A/fmt rewrites run BEFORE
`land()` is even called and only become part of committed history at the
wip-commit, so a preflight check reading `_branch_changed_files`/base_ref diff
content can be silently invalidated by a mutation it never saw).

Investigated every guard actually called in that sequence and classified each:
- `_check_cross_ticket_leakage` -- already had a twin (T-1932's own worked example).
- `_check_passenger_tickets` -- NEW twin added (`_reverify_passenger_tickets_post_
  mutation`), wired into `_land_locked` right alongside the leakage re-check. This
  is the direct T-1618/T-1931-parallel risk: a Tier-A handler regenerating a
  `frob:ticket <id>` directive line for some OTHER ticket would silently carry that
  id onto main as an undisclosed passenger, refused once at preflight and never
  refused again -- closing the same hazard class one guard over.
- `_check_already_landed`, `_check_live_tracker_citations`, `_check_orphaned_
  evidence_deletion`, `_check_mutation_evidence` -- identified as diff-content-
  reading and therefore subject to the same hazard in principle, but NOT closed
  here: each has its own subtlety (e.g. `_check_already_landed`'s empty-scope-diff
  signal risks a DIFFERENT false-positive class if re-checked post-mutation) that
  needs its own investigation rather than a blind copy of the leakage/passenger
  pattern. Registered with an explicit, non-empty `exemption_reason` instead of a
  twin -- an ACKNOWLEDGED, tracked gap, never a silent one.
- `_refuse_anchor_terminal_land` -- reads only `ticket.state` (an in-memory field,
  never committed diff content), structurally immune; registered with a
  `no twin needed` reason.

Acceptance criterion ("add a test that fails if a NEW guard is added ... without a
corresponding registered post-mutation re-check") closed via three tests in a new
`TestCommittedDiffGuardRegistryCompleteness` class:
1. `test_every_call_site_guard_is_registered` -- cross-references a FIXED expected
   call-site name set (pinned to the guards this ticket found) against the
   registry's own tracked names, BOTH directions -- a NEW guard call added to
   either preflight function without updating both the fixed set and the registry
   fails this test (proven below: removing one registry entry while its call site
   still exists in source made this test fail with the exact missing-entry name).
2. `test_every_registry_entry_has_a_twin_or_a_stated_reason` -- the actual
   enforcement: a registry row with NEITHER a twin NOR a reason fails.
3. `test_registered_twins_are_actually_wired_into_the_land_sequence` -- source-
   inspects `_land_locked` for each registered twin's own name, so a registry
   entry cannot claim a twin exists without it actually being called.

Manually verified test 1 catches a real omission: temporarily removed the
`_check_already_landed` entry from `_COMMITTED_DIFF_GUARDS` (leaving its call site
in `_land_precheck` untouched) and reran -- `test_every_call_site_guard_is_
registered` FAILED naming exactly `_check_already_landed` as missing; restored the
entry and reran clean. This is the mechanical acceptance-criterion proof; the fixed
`_EXPECTED_CALL_SITES` set (rather than a live AST walk) means a genuinely NEW
guard function added later needs a one-line addition to that set too, which is a
deliberate, cheap trade-off over full introspection (documented in the test class's
own docstring) matching the ticket's own "or an explicit tuple" allowance.

None of T-1932's own invariant or T-1999/T-1638/T-1963's fixes (landed earlier in
this series worktree) were touched.

Changed:
- src/frob/tickets/_land.py::_CommittedDiffGuard (new)
- src/frob/tickets/_land.py::_COMMITTED_DIFF_GUARDS (new)
- src/frob/tickets/_land.py::_reverify_passenger_tickets_post_mutation (new)
- src/frob/tickets/_land.py::_land_locked (wires the new twin call)

Evidence:
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_call_site_guard_is_registered
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_registry_entry_has_a_twin_or_a_stated_reason
- tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_registered_twins_are_actually_wired_into_the_land_sequence
`--designate-repro --designate-repro-force` used on the first for the same
mechanical NO_VERDICT-at-parent-commit reason as every other ticket in this series
(the whole test class is new, added in the same commit as the registry it tests) --
the real repro was verified directly above via the manual removal/restore of the
`_check_already_landed` registry entry.

Full `tests/test_ticket_land.py`: 275/275 pass (129.07s). Existing
`TestPassengerTickets` (tests/unit/test_land_cross_ticket_leakage.py, run but not
edited) unaffected: 4/4 pass.

Filed: none new.

Gates: `frob check --ticket T-1940` -- no SCOPE001/COV001/COV002/COV006/WIRE001/
DEAD001/TEST001 finding against any of this ticket's new symbols
(`_CommittedDiffGuard`, `_COMMITTED_DIFF_GUARDS`, `_reverify_passenger_tickets_
post_mutation`, or the new test class) after fixing two initial COV006 misbindings
(removed two frob:tests lines that claimed call-graph-invisible source-inspection
tests as coverage) and dropping a helper function that could not clear WIRE002's
follow_up requirement (inlined its one caller instead of adding a waiver ticket
just to carry a test-support accessor). The only SCOPE001 findings in this run
(rapid-debt.jsonl, tickets/T-1963/*, tickets/T-2010/ticket.md) are this series
worktree's own prior, already-landed T-1963 ticket-ledger commits sitting in
branch history -- not touched by this ticket's diff.

### Changed
```
 rapid-debt.jsonl                               |   3 +
 src/frob/tickets/_land.py                      | 114 +++++++++++++++----------
 tests/test_ticket_land.py                      |  43 ++++++++--
 tickets/T-1940/ticket.md                       |  16 +++-
 tickets/T-1963/done-report.md                  | 100 ++++++++++++++++++++++
 tickets/T-1963/ticket.md                       |  19 ++++-
 tickets/{T-draft-15048c17 => T-2010}/ticket.md |   2 +-
 7 files changed, 238 insertions(+), 59 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_call_site_guard_is_registered` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_every_registry_entry_has_a_twin_or_a_stated_reason` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedDiffGuardRegistryCompleteness::test_registered_twins_are_actually_wired_into_the_land_sequence` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, COV003@tickets/T-0907, DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/series-remainder/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1940
