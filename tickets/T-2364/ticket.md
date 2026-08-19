---
id: T-2364
title: frob-cycle gate emits identity-less findings (code=None, file=None) -- an unownable
  finding masked three real cycles
state: in-progress
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/_python.py
- tests/unit/test_check.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: 'narrow to actual producer: frob-cycle findings are built in check/_python.py,
    not gates/__init__.py or cycle/graph.py; gates/__init__.py is leased by T-2551'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/cycle/graph.py
  reason: 'narrow to actual producer: frob-cycle findings are built in check/_python.py,
    not gates/__init__.py or cycle/graph.py; gates/__init__.py is leased by T-2551'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/check/_python.py
  reason: 'narrow to actual producer: frob-cycle findings are built in check/_python.py,
    not gates/__init__.py or cycle/graph.py; gates/__init__.py is leased by T-2551'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_check.py
  reason: 'narrow to actual producer: frob-cycle findings are built in check/_python.py,
    not gates/__init__.py or cycle/graph.py; gates/__init__.py is leased by T-2551'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: T-2364 introduces a new gate rule id CYCLE001 (frob-cycle finding identity);
    frob ticket land refuses close until it is registered in _KNOWN_GATE_RULES per
    the T-0756 new-gate-rule acceptance policy
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_cycle_finding_has_identity_not_none
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_cycle_finding_identity_deterministic_across_runs
- tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_no_cycle_produces_no_diagnostics
designated_repro_test: tests/unit/test_check.py::TestBuildImportGraphAndCycleRealPaths::test_cycle_finding_has_identity_not_none
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
The `frob-cycle` gate producer emits its finding with NO identity:
`code=None, file=None`, the entire description packed into free-text
`message` (a newline-joined chain of file paths). This makes an import
cycle finding UNOWNABLE: it cannot be attributed to a commit, filed by
the rapid sweep, waived, counted in a floor delta, or matched against a
baseline -- it can only be discovered by a human reading raw gate output.

This is not a theoretical concern. It is exactly why a genuine
architectural defect sat undiscovered in this repo's own floor: T-2358
(2026-08-18) found THREE real import cycles via `frob cycle src/frob`,
one of them a hard ERROR-severity 175+-node cross-package
strongly-connected component (serve/stats/tickets/testing/app -- see
T-2363, filed from T-2358's own investigation). None of them had ever
been fixed or even ticketed, because the finding that would have named
them carried no rule id and no file for any tooling -- including the
rapid-sweep auto-filer -- to hang a ticket off of.

T-2345 (landed 2026-08-18) fixed the DOWNSTREAM parse boundary
(`_verify.py::_parse_error_findings_from_json`) to drop a both-empty
diagnostic loudly rather than let it become a real `("", "")` identity
that corrupted the sweep's baseline diffing and (via T-2313's related
incident) deadlocked the verify quarantine for two hours. That fix is
correct and stays -- but its direct consequence is that `frob-cycle`'s
own findings are now DISCARDED at the parse boundary instead of being
silently corrupted. Visibility is not restored by T-2345; it requires
fixing the actual producer, which is this ticket.

REQUIRED: give `frob-cycle`'s violation-emission a real identity:
- A stable rule id (e.g. `CYCLE001`) instead of `None`.
- A representative `file` -- the first (or lowest-sorted) node in the
  cycle's own node list is a reasonable, deterministic choice; whatever
  is chosen must be stable across runs over an unchanged cycle (same
  cycle -> same representative file every time), so two runs of the same
  red state produce the SAME (rule, file) identity for baseline diffing
  and de-duplication to work.
- Keep the full node chain in `message` (free text) unchanged -- that
  detail is genuinely useful and nothing here proposes removing it, only
  adding the missing identity fields alongside it.

Positive controls:
1. A file with a genuine cycle produces a `frob-cycle` finding with a
   non-null `code` and `file`.
2. The SAME cycle, measured twice (no code change in between), produces
   the SAME (rule, file) identity both times (determinism -- required
   for baseline diffing to work at all).
3. `frob check --only cycle`'s existing behavior (severity levels,
   pass/fail, the free-text message content) is otherwise unchanged --
   this is an identity-attachment fix, not a detection-logic change.

Find the producer in `src/frob/gates/` (search for wherever `frob-cycle`
tool results / `Violation`s with `rule=None` currently get constructed --
likely near `frob.cycle.graph.find_cycles`'s own caller in the gates
layer) before assuming a specific file; this ticket's own scope should be
narrowed to whatever that investigation finds, not guessed at here.