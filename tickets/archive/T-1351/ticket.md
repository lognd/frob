---
id: T-1351
title: Scope-filtered check output must disclose what it suppressed (T-1293 false-close
  guard)
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- docs/guides/agent-playbook.md
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check.py
  reason: 'The scope-note fix''s own regression tests live in tests/unit/test_check.py

    (the existing home for _run_gates/_gates_success_result unit tests, per

    the file''s own established precedent for this exact function family).

    Needed for COV002 (frob:ticket edge) and SCOPE001 (declared scope) to

    pass on the code these tests actually cover.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run
- tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped
- tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure
designated_repro_test: null
acceptance:
- text: given frob check --ticket T-XXXX, when it reports a gate as clean, then the
    output states that the run was scope-filtered and how many findings were suppressed
    outside that scope
  evidence:
  - tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run
  - tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped
  - tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure
threat: null
component: check
---
Filed 2026-07-31 as the GUARD for the T-1293 false-close (see the perf burn-down successor). An audit finding gets two tickets: the fix, and the thing that would have caught it. This is the latter.

THE DEFECT: "frob check --only test --ticket T-XXXX" filters findings to the ticket's declared scope. An agent that runs it and sees "0 findings" reasonably concludes its package is clean. It is not -- the scope is typically much narrower than the package, and the unscoped gate may still show dozens of findings. On T-1293 this produced a confidently-reported false green that survived land AND close, and was caught only by an out-of-band coordinator re-measure.

This is the "catalogued is not enforced" failure mode in a new place: a completion claim backed by a number that does not mean what the reader thinks it means.

PROPOSALS (pick per implementation reality, do not assume):
1. When a check run is scope-filtered by --ticket, SAY SO in the output and in the summary line -- e.g. "gate:TEST 0 errors (FILTERED to T-1293's scope; 65 findings exist outside it)". The suppressed count is the load-bearing number and is currently invisible. This alone would have prevented the incident.
2. Make TEST005's own finding text name the measurement command that produces the number the gate reads, so an agent cannot substitute a scoped pytest --cov run by accident.
3. Consider whether a coverage-derived gate should refuse to report at all when the coverage stamp is stale or absent, rather than silently reporting against old data.
4. Document the measurement protocol in docs/guides/agent-playbook.md: how to measure a coverage-gated burn-down, and that a --ticket-scoped zero is not a package zero.

BLOCKER ASSESSMENT: T-1335 is already open on "make coverage" (stamp failure not propagated, stale fixture paths break coverage xml). If the repo-wide coverage stamp is unreliable or unrefreshable by a worktree agent, then EVERY TEST005 burn-down ticket is unverifiable by the agent working it -- which makes T-1335 a blocker for the entire burn-down campaign rather than a side issue. Assess this and, if confirmed, record the dependency explicitly.