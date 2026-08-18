## Done report

Mutation-verb survey (frob ticket priority/kind/component/label/tier/
sprint/runs-last/block, plus the pre-existing scope/accept/drop/anchor):

  priority       -- NO --reason (before this ticket)
  kind           -- NO --reason (before this ticket)
  component      -- NO --reason (before this ticket)
  tier           -- NO --reason (before this ticket)
  label          -- NO --reason (freeform tag, deliberately documented
                     as carrying no lease-conflict audit trail --
                     left alone, not triage-relevant classification)
  sprint assign  -- NO --reason (freeform commitment label; left alone,
                     same rationale as label -- outside this fix's scope)
  runs-last      -- NO --reason (ordering marker, not a triage-priority
                     field; left alone)
  block          -- has --by TICKET_BY (records the blocking id) but no
                     free-text why; left alone, a distinct mechanism
  scope          -- REQUIRES --reason/--reason-file (T-0455/T-0737),
                     records scope_changes
  accept --amend/--remove -- REQUIRES --reason/--reason-file (T-1422),
                     records acceptance_amendments
  scope-ack      -- REQUIRES --reason/--reason-file (T-1484)
  anchor         -- REQUIRES --reason/--reason-file (T-1856/T-1867)
  drop           -- REQUIRES --reason (T-0579)
  evidence --replace -- REQUIRES --reason/--reason-file (T-1733)

Fix: priority/kind/component/tier -- the four single-value TRIAGE
classification setters, same parser/setter shape as each other and the
ones the ticket's own incident named -- now require --reason/
--reason-file (T-0737 pattern), recorded into a new triage_changes
audit trail (TriageChangeEntry: field, old_value, new_value, reason,
actor, at), mirroring ScopeChangeEntry/AcceptanceAmendmentEntry rather
than inventing a new mechanism. label/sprint/runs-last/block are left
untouched -- label is explicitly documented as carrying no audit trail
by design, sprint/runs-last are ordering/commitment markers rather than
triage classification, and block already has its own --by mechanism;
widening the fix to all eight was judged scope creep beyond the
ticket's own motivating incident (a priority re-triage) and its named
precedent pair (scope/accept).

set_kind's existing kind_history mechanism (T-1616, conditional on
evidence/Done-report state) is kept as-is and unconditionally
supplemented by the new triage_changes entry -- the two serve different
purposes and neither replaces the other.

POSITIVE CONTROLS (all four verbs, library level):
- test_reason_missing_refuses (priority/kind/component/tier): a blank/
  whitespace-only reason returns Err(TicketError.TriageReasonMissing).
- test_reasoned_change_records_triage_entry (priority): a reasoned
  change appends one TriageChangeEntry with field/old_value/new_value/
  reason all correctly populated.
- Existing test_updates_*_field tests (all four) confirm the ordinary
  reasoned path still succeeds -- the query-only verbs (list/show/
  doable/board/...) were not touched and remain reason-less by design.

Out-of-scope discoveries filed: none new -- the label/sprint/runs-last/
block "left alone" decisions above are disclosed here rather than
silently dropped, per playbook TICK011.

frob check --ticket T-2353: 0 findings attributable to this ticket's
own touched files (OPAQUE001/ARCH001/WIRE001/SCOPE001/COV005/PRE001
all found and fixed during the pass; remaining findings are pre-existing
and repo-wide per the --ticket scope-note). ruff (--only ruff): 1 error
total, in src/frob/verify/_worker.py, pre-existing on main and outside
this ticket's scope.

pytest (targeted): all new/changed tests pass; the sole failure seen
(TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree,
T-1892 EvidenceCmdSilent) reproduces identically on main HEAD before
this change and is unrelated.

### Changed
```
 tickets/T-2353/done-report.md |  85 ++++++++++++++++++++++++++
 tickets/T-2353/ticket.md      | 139 +++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 222 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestSetPriority::test_updates_priority_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestSetPriority::test_reason_missing_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestSetPriority::test_reasoned_change_records_triage_entry` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_updates_kind_field` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestSetKind::test_reason_missing_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestSetComponent::test_updates_component_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_organization.py::TestSetComponent::test_reason_missing_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSetTier::test_updates_tier_field` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSetTier::test_reason_missing_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2353/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2353, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
