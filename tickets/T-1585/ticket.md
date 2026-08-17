---
id: T-1585
title: 'rapid profile: evidence/done-report leniency for docs/chore, REL001 off, baseline-thread-free
  land'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_tickets.py
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/**
  reason: verified all 3 described relaxations already implemented by T-1681/T-1705/T-1684;
    this ticket's own remaining work is regression coverage for item 1's backstop,
    narrowing to the one test file touched
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets.py
  reason: verified all 3 described relaxations already implemented by T-1681/T-1705/T-1684;
    this ticket's own remaining work is regression coverage for item 1's backstop,
    narrowing to the one test file touched
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/tickets/**
  reason: narrow to the read-only-verified file plus the test file touched; no production
    code changed
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: narrow to the read-only-verified file plus the test file touched; no production
    code changed
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_missing_evidence_and_done_report_proceeds_with_debt_recorded
- tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_non_rapid_missing_evidence_and_done_report_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed while working T-1575: rapid profile's TEST016-skip and pre-commit-sweep-skip seams landed; three remaining rapid semantics from T-1575's body are still open: (1) evidence/done-report requirements light for kind=docs/chore, (2) REL001 off under rapid, (3) no baseline snapshot worktree at all -- today rapid still runs the T-1463 baseline thread because _land_cmd.py's post-land sweep reads the same result. Ledger integrity and LAND-PROOF stay non-negotiable in every profile.

## Done report

Changed: `tests/test_tickets.py` -- two new regression tests,
`TestDoneTransitionStructuralGuardRapidLeniency`. No production code
changed; this ticket's three described relaxations were already
implemented by other, earlier tickets (checked before writing anything,
per the coordinator's "re-measuring first has been cheaper than
implementing twice" instruction).

Evidence:
`tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_missing_evidence_and_done_report_proceeds_with_debt_recorded`,
`tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_non_rapid_missing_evidence_and_done_report_still_refuses`.

Filed: none.

## Summary: all three described relaxations, verified already shipped

**Item 1 (evidence/done-report leniency for docs/chore)**: implemented,
but BROADER than described -- `_done_transition_structural_guard`
(`src/frob/tickets/_evidence.py`) relaxes for EVERY kind under `rapid`,
not just `docs`/`chore` (T-1681; note "chore" is not even a real
`TicketKind` member -- FEATURE/BUG/SECURITY/UX/DOCS/INVARIANT/INCIDENT
are the only seven). No test exercised the function's `rapid=True`
branch end to end before this change -- added one.
**Backstop**: `debt_sink` (wired to `record_rapid_debt`,
`rapid-debt.jsonl`, a TRACKED file) is invoked on every relaxed close,
unconditionally -- verified by assertion in the new test, not just by
reading the source. The relaxation is visible/auditable, not silent;
this repo's own log line at land time says explicitly "every commit
made in this state needs the T-1681 re-verification pass before the
relaxation is considered discharged" (`_profile.py`), i.e. there is a
real downstream consumer of this debt log, not a write-only audit
trail.

**Item 2 (REL001 off under rapid)**: implemented (T-1705,
`_close_cmd.py::_maybe_skip_rel001_preflight`-shaped function around
line 440). **Backstop**: same `record_rapid_debt` mechanism, same
downstream re-verification consumer -- verified by reading the call
site (`record_rapid_debt(root, ticket.id, "close-rel001-preflight-
skipped")` runs unconditionally on the skip path), not independently
tested here (pre-existing, out of this ticket's remaining scope to
re-verify further given the other two items already needed the time).

**Item 3 (no baseline-snapshot worktree)**: implemented (T-1684,
`_land_cmd.py::_land_core_start_baseline`, `rapid_land=True` branch
starts a no-op thread instead of the real T-1463 capture).
**Backstop**: NOT "nothing catches this anymore" -- the docstring and
module-level `_profile.py` comment are explicit that the check is
DEFERRED, not dropped: "the post-land sweep is deferred to a detached
child that diffs against its own rolling baseline
(`frob.app.ticket_runner._rapid_sweep`) ... has no consumer under that
profile" -- i.e. the synchronous pre-land JOIN this ticket's body
complained about (a full `frob check` the land had to wait on) is gone,
but the check itself still runs, asynchronously, with revert-on-red
per `docs/strata`... (this repo's own rapid-profile docs, not re-cited
in full here since `_rapid_sweep.py` is off-limits to touch or deeply
verify this dispatch -- another agent owns it).

**Confirmed still true, per the coordinator's explicit ask**: grepped
`rapid`/`ProfileName.RAPID` across `_land.py` (read-only, not touched)
for any co-occurrence with ledger-integrity or LAND-PROOF logic -- zero
hits. The "ledger integrity and LAND-PROOF verification are NOT
relaxed" line in `_profile.py`'s own docstring stays true as far as this
dispatch could verify without touching the file that would need editing
to break it.

No implementation work remained once the above was verified -- this
ticket's body describes a set of relaxations, all three already exist,
and the one gap (missing regression coverage on item 1, the one with no
existing test at all) is now closed. Recommending CLOSE, not drop: real
new evidence was produced, even though no production behavior changed.

Gates: `tests/test_tickets.py -k TestDoneTransitionStructuralGuardRapidLeniency`
2/2 pass.

### Changed
```
 tests/test_tickets.py    | 45 +++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1557/ticket.md | 37 ++++++++++++++++++++++++++++++-------
 tickets/T-1585/ticket.md | 36 +++++++++++++++++++++++++++++++++---
 3 files changed, 108 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_missing_evidence_and_done_report_proceeds_with_debt_recorded` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_non_rapid_missing_evidence_and_done_report_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t1557-t1585/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1557-t1585/tests/unit/test_tickets_evidence_only_scope.py
