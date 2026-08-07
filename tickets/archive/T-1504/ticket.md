---
id: T-1504
title: 'warning burn-down: TICK011/TICK007, COV remainder, REF, WALK, DEPR, LANG classes'
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- frob.toml
- src/frob/refactor/_scan.py
- src/frob/tickets/_store.py
- src/frob/tickets/_renumber_v2.py
- src/frob/app/docs_runner.py
- src/frob/app/xref_runner.py
- src/frob/app/map_runner.py
- src/frob/app/outline_runner.py
- tests/unit/test_land_release_coherence.py
- tests/test_refactor.py
- docs/index.md
- docs/audits/README.md
- invariants/INV-002.md
- invariants/INV-011.md
- invariants/INV-029.md
- invariants/INV-041.md
- src/frob/gates/_sys.py
- src/frob/gates/_docenum.py
- src/frob/app/config.py
- src/frob/app/stats_runner.py
- src/frob/graph/cache.py
- src/frob/outline/__init__.py
- src/frob/vet/_scan.py
- strata-core/src/parse/grammar_core.rs
- strata-core/src/parse/grammar_infra.rs
- strata-core/src/parse/grammar_node.rs
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
- src/frob/gates/__init__.py
- src/frob/gates/_decisions_compliance.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_todo_fmt.py
- src/frob/gates/_waive.py
- tests/test_gates.py
- tests/test_tickets_gate_claim_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/**
  reason: actual work is ledger addenda (TICK011 cites) + filing a follow-up draft,
    not broad src/**/docs/** editing
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: actual work is ledger addenda (TICK011 cites) + filing a follow-up draft,
    not broad src/**/docs/** editing
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tickets-archive.md
  reason: actual work is ledger addenda (TICK011 cites) + filing a follow-up draft,
    not broad src/**/docs/** editing
  actor: logan
  at: '2026-08-03'
- op: add
  glob: frob.toml
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/refactor/_scan.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_store.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/tickets/_renumber_v2.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/docs_runner.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/xref_runner.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/map_runner.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/outline_runner.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_land_release_coherence.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_refactor.py
  reason: widening from ledger-only to the specific WALK001/DEPR003/DEAD001/REF001
    fix sites this drain-to-zero ticket touches
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/index.md
  reason: REF002 second-inbound-reference fix for two orphan-fragile audit docs
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/README.md
  reason: REF002 second-inbound-reference fix for two orphan-fragile audit docs
  actor: logan
  at: '2026-08-03'
- op: add
  glob: invariants/INV-002.md
  reason: REF003 stale frob:used-by anchors after file splits (T-1152/dup/sys/threat)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: invariants/INV-011.md
  reason: REF003 stale frob:used-by anchors after file splits (T-1152/dup/sys/threat)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: invariants/INV-029.md
  reason: REF003 stale frob:used-by anchors after file splits (T-1152/dup/sys/threat)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: invariants/INV-041.md
  reason: REF003 stale frob:used-by anchors after file splits (T-1152/dup/sys/threat)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_sys.py
  reason: 'REF003 fix: correct reaching consumer for INV-041'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_docenum.py
  reason: TODO002 rebind for dangling frob:todo draft id
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/stats_runner.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/graph/cache.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/outline/__init__.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/vet/_scan.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: strata-core/src/parse/grammar_core.rs
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: strata-core/src/parse/grammar_infra.rs
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: strata-core/src/parse/grammar_node.rs
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/conftest.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_decisions_compliance.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_todo_fmt.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_tickets_gate_claim_evidence.py
  reason: 'coordinator extension: WAIVE004 stale-waiver drain (~41/20 findings) after
    main merge proved suite green'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_refactor.py::TestFindPythonFiles::test_finds_py_files_and_skips_venv
- tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_reads_pyproject_version_from_disk
- tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_already_coherent_is_noop
designated_repro_test: null
threat: null
component: null
---
Drain-to-zero drive: warning burn-down across TICK011, TICK007, COV006/COV007
remainder, REF, WALK, DEPR, LANG conformance classes.

Get live lists via:
uv run frob check --only tickets --only coverage --only refs --only walk_lint \
  --only deprecated --only lang_conformance

1. TICK011 (~22): disclosed cuts with no ticket -- for each, find the
   disclosing Done report, then either file the missing follow-up ticket
   (drafts fine) or record why not in the report addendum.
2. TICK007 (~4): read the finding text, remediate per its instruction.
3. COV006 (~12) / COV007 (~9 remaining): rebind test edges to reachable
   symbols (read each test); move private doc anchors to public callers or
   keep with a written reason.
4. REF (~9), WALK (~4), DEPR (~4), LANG (~3), TODO (1), DEAD (1): read each
   finding and fix or waive-with-reason per its own remediation text.

Close with an evidence-cmd capturing before/after per class.