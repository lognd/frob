---
id: T-1231
title: 'doclink basename+fragment validation -- resolve relative link targets and
  #fragment anchors'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/gates/_doclink.py
- src/frob/gates/_doclink_docanchor.py
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_waive.py
- docs/design/registry/check-coverage.yaml
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
  glob: src/frob/gates/_doclink.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: 'T-1231: _doclink.py was merged into _doclink_docanchor.py (T-1170) before
    this ticket started; scope target renamed, not removed'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1231: DOC008 needs a gates.md table row + docstring anchor, a waive-registry
    entry, and its own test coverage in test_gates.py'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1231: DOC008 needs a gates.md table row + docstring anchor, a waive-registry
    entry, and its own test coverage in test_gates.py'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1231: DOC008 needs a gates.md table row + docstring anchor, a waive-registry
    entry, and its own test coverage in test_gates.py'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1231: DOC008 needs its own CHK-GATE-DOC008 registry entry and denominator
    bump'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestDoclinkGate::test_broken_relative_link_target_fires_doc008
- tests/test_gates.py::TestDoclinkGate::test_broken_fragment_on_existing_target_fires_doc008
- tests/test_gates.py::TestDoclinkGate::test_resolvable_relative_link_and_fragment_pass
designated_repro_test: null
threat: null
component: null
---
Extend doclink checking (DOCLNK rule) to verify relative link basenames and #fragment anchors resolve, or fail. Ref: gate-gap class 5 in docs/audits/docs-staleness-2026-07-29.md.