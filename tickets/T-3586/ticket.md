---
id: T-3586
title: Split tests/test_gates.py (21691 lines) into a per-gate-family package via
  frob refactor verbs; establish the monofile-split recipe
state: done
kind: feature
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
- tests/gates_suite/**
- tests/conftest.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: split relocated capability-observing test code; via-lists must follow the
    files 1:1 (515 SELFAUDIT001 findings from the land attempt are the spec)
  actor: logan
  at: '2026-09-01'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: split relocated capability-observing test code; via-lists must follow the
    files 1:1 (515 SELFAUDIT001 findings from the land attempt are the spec)
  actor: logan
  at: '2026-09-01'
evidence:
- tests/gates_suite/test_prework.py::TestScopePrework::test_pre001_missing_sweep
- tests/gates_suite/test_doc.py::TestDriftGate::test_drift001_stale_ack_has_remedy
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov001_waiver_does_not_blanket_suppress_sibling_symbol
- tests/gates_suite/test_waive.py::TestWaivePresets::test_waive_preset_resolves_reason_and_matches_like_inline
- tests/gates_suite/test_wire.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
- tests/gates_suite/test_protocol.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
- tests/gates_suite/test_debt.py::TestDebtGate::test_debt002_closed_ticket_is_reported
- tests/gates_suite/test_invariant.py::TestInvariantGate::test_inv001_no_evidence
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test001_public_symbol_no_unit_edge
- tests/gates_suite/test_run.py::TestRunGates::test_run_gates_end_to_end
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_tick006_renamed_draft_resolved_via_git_not_refiled
- tests/gates_suite/test_sys.py::TestSysGate::test_noop_no_design_dir
- tests/gates_suite/test_tick.py::TestTick006PhantomFiling::test_backtick_styled_id_in_a_real_claim_still_fires
- tests/gates_suite/test_compliance.py::TestPiiStructuralCrossLanguage::test_ts_interface_email_field_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER REQUEST (2026-08-31): the monofile test suites must be split, using
the frob refactor verbs, into new folders. MEASURED (wc -l):
    21691 tests/test_gates.py
    12596 tests/test_ticket_land.py
     8910 tests/unit/test_arch.py
     7992 tests/test_vet.py
     5935 tests/unit/test_coordinator_scripts.py
     5055 tests/unit/test_rapid_sweep.py
This ticket owns the FIRST split (tests/test_gates.py) and establishes the
recipe the follow-ups reuse; file one follow-up per remaining file above.

METHOD (non-negotiable -- this is why the refactor verbs exist):
 1. Plan the grouping: cluster test_gates.py's test classes by gate family
    (the file's own section comments and class names make this mechanical:
    scope/prework, doc, coverage, waive, arch, perf, tick, land-parity...).
    Target: a new package tests/gates_suite/ (or tests/test_gates/ --
    pick what conftest collection ordering and the T-2099
    heavy_subprocess-by-module grouping handle cleanly; state the choice)
    with one module per family, each well under LARGE001's 800-line
    threshold where practical, never above ~2000.
 2. Move with `uv run frob refactor split` / `move-module` ONLY -- never
    hand-copy: the verbs rewrite every reference, which is what keeps the
    repo-wide frob:tests directives, ticket evidence citations, and
    doc/test edges pointing at the moved node ids. Hand-moving orphans
    OTHER tickets' evidence (the T-2114 family and the archived-evidence
    trap) -- measured repeatedly in this repo's history.
 3. After each batch of moves, prove closure: `uv run frob check --only
    docblocks --only test --only coverage --budget 300` shows ZERO new
    DOC007/TEST/COV errors versus before (capture the before counts
    first), and `git grep -c 'test_gates.py::'` outside tests/ returns
    only intentionally-updated references.
 4. Preserve per-test markers (xdist_group, timeout, heavy_subprocess
    module grouping -- moving a class to a new module CHANGES its
    T-2099 group key: state the effect on peak memory and keep heavy
    real-git classes in dedicated modules).
 5. The suite must pass identically: run the moved families by node id
    plus `uv run frob test`; the CI collection count must not drop
    (13054 +/- intentional).
ACCEPTANCE: tests/test_gates.py either deleted or reduced to a thin
re-export shim under 200 lines (state which and why); zero new gate
errors; follow-up tickets filed for the other five files with this
ticket's recipe cited.

## Failure log
- 2026-08-31 attempt 1: refactor split/move/move-module cannot address tests/** (module_to_path hardcodes src/ as sole root, T-3587 filed); hand-moving is forbidden by the ticket's own method