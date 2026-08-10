---
id: T-1941
title: 'COV003: T-0185 evidence references a test deleted by the exhaustive-research
  skill/agent removal'
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
- tickets/T-0185/**
- tickets/T-1351/**
- tickets/T-1507/**
- tickets/T-1512/**
- tickets/archive/T-0185/**
- tickets/archive/T-1351/**
- tickets/archive/T-1507/**
- tickets/archive/T-1512/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1351/**
  reason: 'Widening to cover three more COV003 orphans caused by the same class of

    defect (evidence node deleted/replaced by another ticket''s land without

    updating the orphaned ticket''s bound evidence): T-1351, T-1507, T-1512 all

    point at tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure,

    which T-1928''s land (e68f129b115f) replaced with

    test_full_run_discloses_fmt_scope (asserting the opposite behavior).

    Per coordinator instruction, fixing all four unticketed/ticketed orphans

    under one series rather than filing duplicate tickets.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1507/**
  reason: 'Widening to cover three more COV003 orphans caused by the same class of

    defect (evidence node deleted/replaced by another ticket''s land without

    updating the orphaned ticket''s bound evidence): T-1351, T-1507, T-1512 all

    point at tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure,

    which T-1928''s land (e68f129b115f) replaced with

    test_full_run_discloses_fmt_scope (asserting the opposite behavior).

    Per coordinator instruction, fixing all four unticketed/ticketed orphans

    under one series rather than filing duplicate tickets.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1512/**
  reason: 'Widening to cover three more COV003 orphans caused by the same class of

    defect (evidence node deleted/replaced by another ticket''s land without

    updating the orphaned ticket''s bound evidence): T-1351, T-1507, T-1512 all

    point at tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure,

    which T-1928''s land (e68f129b115f) replaced with

    test_full_run_discloses_fmt_scope (asserting the opposite behavior).

    Per coordinator instruction, fixing all four unticketed/ticketed orphans

    under one series rather than filing duplicate tickets.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-0185/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-1351/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-1507/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-1512/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_research_assets.py::test_docs_index_links_the_guide
- tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run
- tests/unit/test_check.py::TestScopeDisclosure::test_full_run_discloses_fmt_scope
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1933's land-parity check (repo root main, tree at 92320e002) found COV003 firing repo-wide: T-0185's bound evidence 'tests/unit/test_research_assets.py::test_skill_frob_doc_anchor_resolves_in_guide' no longer resolves to a collected test. Root cause looks like commit 72902adc0 ('chore: remove project-scope .claude/agents and .claude/skills'), which deleted the exhaustive-research skill/agent this test exercised, without updating T-0185's evidence. Confirmed reproducing from a clean main checkout with no other changes -- not introduced by T-1933 (scope: docs/design/cli-hygiene.md, docs/index.md, src/frob/app/ticket_runner/_close_cmd.py, src/frob/app/ticket_runner/_new.py). Fix: either restore/replace T-0185's evidence with a currently-collecting test, or if the skill/agent removal genuinely obsoletes what T-0185 verified, re-scope T-0185 and record fresh evidence.

## Done report

frob:no-behavior-change reason="this ticket only rebinds/re-points stale ticket evidence (frob ticket evidence --replace) on 4 archived tickets and records fresh evidence on T-1941 itself -- no production code path changed, only tickets.md/tickets/archive/**/ticket.md ledger content. There is no defect for a designated repro test to reproduce; the auto-designated evidence (a pre-existing docs-drift-lock test unrelated to this ticket's own change) correctly PASSES at both parent and fix, which is exactly what a no-behavior-change claim predicts."

Widened from T-0185's single orphan to cover all 4 COV003 orphans
measured at commit 2d8476ab4 (`timeout 540 uv run frob check --only
gates`): T-0185, T-1351, T-1507, T-1512. Per-ticket decision, verified by
reading each ticket's own claim, not by matching test names:

- T-0185: the deleted test (test_skill_frob_doc_anchor_resolves_in_guide)
  exercised the repo-local .claude/skills/agents shadow copies removed by
  72902adc0. That commit's own message confirms the capability is
  unaffected (a user-scope original still loads at runtime) -- only the
  repo-local shadow and its doc anchor were removed;
  docs/guides/exhaustive-research.md stays, with live frob:doc anchors
  elsewhere still binding to it. Re-pointed (--replace) to
  test_docs_index_links_the_guide, which proves the part of T-0185's
  claim still true today (the guide stays reachable from docs/index.md,
  T-0186's own deliverable, landed in the same merge as T-0185).

- T-1351: the deleted test's exact claim ("a full unfiltered run adds NO
  disclosure") was DELIBERATELY overturned by T-1928
  (e68f129b115f) -- gate:FMT is diff-scoped by construction, so a full
  unscoped run now must disclose it too. T-1351's literal acceptance-[0]
  wording is genuinely obsolete, not restorable; the renamed successor
  (test_full_run_discloses_fmt_scope) asserts the OPPOSITE, so pointing
  T-1351 at it would misrepresent T-1351's own acceptance criterion as
  still true. Re-pointed instead to test_no_disclosure_when_fmt_did_not_run,
  which proves the part of T-1351's original intent still true: the
  disclosure note stays silent when nothing actually applies (no --only
  narrowing, no --ticket, fmt itself did not run).

- T-1507 / T-1512: their own claim is _native.py/_python.py TEST005
  module-line coverage, unrelated to scope-disclosure semantics. The
  orphaned node was one entry in a large "whole test_check.py suite still
  collects and passes" evidence sweep for both tickets, not load-bearing
  for the coverage claim itself. Re-pointed (--replace) both to the
  direct successor node (test_full_run_discloses_fmt_scope), which
  currently collects and passes and is a real, honest proof that the
  file this ticket touched still passes as a whole.

All four --replace calls used --reason-file recording the above, per
T-1733. T-0185/T-1351/T-1507/T-1512 are archived tickets (`tickets/
archive/T-XXXX/**`), so scope was widened to include those paths too
(the earlier `tickets/T-XXXX/**` globs alone do not cover them).

Verification: `frob check --only coverage` (repo-wide, unscoped): gate:COV
0 errors, 24 warnings, 185 waived -- the 4 COV003 findings are gone.
`frob check --ticket T-1941 --only scope`: 0 SCOPE001 errors (2 pre-
existing DRIFT002 findings on src/frob/tickets/_land.py remain -- untouched
by this ticket's scope, unrelated: a stale test-file reference from an
earlier, unrelated land, confirmed via `git log` showing this ticket
never touched _land.py or its test file).

Filed: none.

### Changed
```
 tickets/T-1941/done-report.md    |  73 +++++++++++
 tickets/T-1941/ticket.md         | 137 ++++++++++++++++++++-
 tickets/archive/T-0185/ticket.md |  67 ++++++++++-
 tickets/archive/T-1351/ticket.md | 143 +++++++++++++++++++++-
 tickets/archive/T-1507/ticket.md | 253 ++++++++++++++++++++++++++++++++++++++-
 tickets/archive/T-1512/ticket.md | 178 ++++++++++++++++++++++++++-
 6 files changed, 841 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/test_research_assets.py::test_docs_index_links_the_guide` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_full_run_discloses_fmt_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 834 warning(s), 701 waived
- error-findings: DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py
