---
id: T-1339
title: Suppression-dialect compliance is automatic, never hand-maintained
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- src/frob/gates/_waive.py
- src/frob/gates/_fix_engine.py
- src/frob/gates/_suppress.py
- src/frob/gates/_fix_engine_text.py
- tests/test_gates_suppress.py
- tests/test_gates_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_suppress.py
  reason: T-1339's acceptance criteria (SUPPRESS001 detection, frob check --fix auto-pairing)
    were implemented across T-1340/T-1341 (phases 1-2) in _suppress.py/_fix_engine_text.py,
    not in the originally-declared _waive.py; verification work for this closing ticket
    needs those real files and their real tests in scope
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_fix_engine_text.py
  reason: T-1339's acceptance criteria (SUPPRESS001 detection, frob check --fix auto-pairing)
    were implemented across T-1340/T-1341 (phases 1-2) in _suppress.py/_fix_engine_text.py,
    not in the originally-declared _waive.py; verification work for this closing ticket
    needs those real files and their real tests in scope
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_suppress.py
  reason: T-1339's acceptance criteria (SUPPRESS001 detection, frob check --fix auto-pairing)
    were implemented across T-1340/T-1341 (phases 1-2) in _suppress.py/_fix_engine_text.py,
    not in the originally-declared _waive.py; verification work for this closing ticket
    needs those real files and their real tests in scope
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: T-1339's acceptance criteria (SUPPRESS001 detection, frob check --fix auto-pairing)
    were implemented across T-1340/T-1341 (phases 1-2) in _suppress.py/_fix_engine_text.py,
    not in the originally-declared _waive.py; verification work for this closing ticket
    needs those real files and their real tests in scope
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
- tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression
- tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op
- tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean
designated_repro_test: null
acceptance:
- text: given a line carrying one checker's suppression and an unsuppressed diagnostic
    from another configured checker, when frob check runs, then SUPPRESS001 reports
    it
  evidence:
  - tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires
  - tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean
- text: given SUPPRESS001 findings, when frob check --fix runs, then the paired suppression
    is written with the reporting checker's own rule code, in canonical order, idempotently
  evidence:
  - tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression
  - tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op
threat: null
component: gates
---
User directive (2026-07-31): 'auto-detect mypy waivers and make an additional ty waiver and vice-versa ... all this tool compliance stuff should be automatically handled rather than manually done.'

Motivating incident: two ty errors on main (tests/test_fuzz.py:159 unresolved-reference, tests/test_tickets_collision.py:826 unresolved-attribute) were NOT type defects -- both lines already carried a mypy 'type: ignore' that ty does not honor. Both were hand-fixed. Per the systematize-friction mandate, repeated dev friction becomes tooling, not repeated hand-work.

DESIGN (decided, see leaves): pairing is EVIDENCE-DRIVEN, not static. The gate fires only where checker B emits an unsuppressed diagnostic on a line that already carries checker A's suppression. This avoids the two failure modes of naive static pairing: (a) mypy/ty rule codes are not 1:1 (name-defined vs unresolved-reference, attr-defined vs unresolved-attribute), so static pairing needs a lossy mapping table; (b) stamping suppressions onto lines the other checker never flagged just creates unused-suppression debt. Evidence-driven pairing needs NO mapping table -- the reporting checker's diagnostic carries the exact rule code to emit.

Current population: 37 'type: ignore' lines, 20 already dual-dialect, 17 mypy-only, 6 ty-only.

DESIGN AMENDMENT (2026-07-31, user, SUPERSEDES the configuration-gating decision above): the GOAL IS PORTABILITY, not conformance to whichever checker this repo happens to run. 'This repo runs ty, but that doesn't mean every repo runs ty; I just want anybody to be able to type-check the code.' A downstream consumer running mypy against frob's source must not eat spurious errors, so every suppressed line should carry EVERY supported dialect's suppression -- including for checkers this repo never runs.

Consequences, all of which reverse earlier decisions:
1. Do NOT gate a direction on the tool being configured in the consuming project. Silence-when-unconfigured was correct for a conformance goal and is WRONG for a portability goal -- it would leave frob's own source hostile to mypy users forever, since mypy never runs here.
2. Do NOT drop the mypy dialect or migrate the 17 legacy mypy-only ignores away. They are load-bearing for downstream mypy users. The successor question posed in T-1342 is withdrawn.
3. mypy becomes a DEV DEPENDENCY used purely as an ORACLE (user-sanctioned: 'If we need to get mypy purely for testing this capability, then we can go ahead and do so'). ty stays the gating checker; mypy is never a gate, only a source of ground-truth diagnostics.

This amendment RESCUES the evidence-driven design rather than forcing a retreat to static pairing. The reason evidence-driven pairing looked impossible for an unconfigured checker is that nothing produced its diagnostics; installing mypy as an oracle produces exactly those diagnostics locally. So pairing stays evidence-driven and SYMMETRIC, still needs NO mypy-code <-> ty-code mapping table, and each dialect's suppression is written with that dialect's own rule code taken from that dialect's own diagnostic. Static pairing with a lossy mapping table remains rejected.

Watch item for the oracle: mypy's --warn-unused-ignores must stay OFF, or be reconciled deliberately. Exact evidence-driven pairing should not produce unused ignores, but the 17 pre-existing legacy mypy ignores were written for a mypy that never ran and some may now be unused; treat any such finding as information, never as license to delete a suppression a downstream consumer may need.