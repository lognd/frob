---
id: T-1402
title: 'Gate precision for v1.0.0: EXHAUST001 and TICK011 fire where no honest fix
  exists'
state: done
kind: feature
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: epic
sprint: null
scope:
- src/frob/gates/_exhaustive_handling.py
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
- src/frob/app/ticket_runner/_mutate.py
- src/frob/check/_python.py
- src/frob/check/_ts.py
- src/frob/deploy/_conform.py
- src/frob/doctor.py
- src/frob/dup/_pipeline/_probe.py
- src/frob/dup/_pipeline/_smt.py
- src/frob/fuzz/_signatures.py
- src/frob/gitio.py
- src/frob/gitlog/__init__.py
- src/frob/lang/__init__.py
- src/frob/lang/_nodes.py
- src/frob/mutate/__init__.py
- src/frob/mutate/_journal.py
- src/frob/natives/_build.py
- src/frob/outline/__init__.py
- src/frob/process/parsers/valgrind.py
- src/frob/scaffold/_managed.py
- src/frob/serve/_events.py
- src/frob/serve/_socketd.py
- src/frob/serve/_warm.py
- src/frob/strata/_claims.py
- src/frob/strata/_code_binding.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_facts.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_mode_conformance.py
- src/frob/strata/_native_staleness.py
- src/frob/strata/_obligation_proof.py
- src/frob/strata/_reliability.py
- src/frob/testing/_collect_cpp.py
- src/frob/testing/_runners.py
- src/frob/xref/__init__.py
- tests/test_gates.py
- docs/strata/host.md
- docs/guides/install.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_tickets.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/modules/gates.md
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/check/_python.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/check/_ts.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/doctor.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/dup/_pipeline/_probe.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/dup/_pipeline/_smt.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/fuzz/_signatures.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/gitio.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/gitlog/__init__.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/lang/__init__.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/lang/_nodes.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/mutate/_journal.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/natives/_build.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/outline/__init__.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/process/parsers/valgrind.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/scaffold/_managed.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/serve/_events.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/serve/_socketd.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/serve/_warm.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_claims.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_code_binding.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_elaborate.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_facts.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_host_isolation.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_mode_conformance.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_obligation_proof.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/strata/_reliability.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/testing/_collect_cpp.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/testing/_runners.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/xref/__init__.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tests/test_gates.py
  reason: 'Declared scope named src/frob/gates/_tickets.py, which does not exist;
    the

    real TICK011 gate module is src/frob/gates/_tickets_gate.py (a typo in the

    ticket body). Widening to that real path, plus src/frob/gates/_waive.py

    (the _KNOWN_GATE_RULES allowlist a new rule id must be added to for

    frob:waive to accept it at all -- WAIVE002 would otherwise flag any

    waiver naming EXHAUST003 as targeting a rule that can never match), plus

    every other source file whose existing frob:waive EXHAUST001 comment

    became stale once EXHAUST001 was narrowed (the leaked Unknown at each of

    those sites traces to an unresolved callee, not an own bare re-raise, so

    each now fires EXHAUST003 instead -- left as EXHAUST001 they would each

    become a fresh WAIVE002 finding: "waiver for a rule that can never match

    there"), plus docs/design/registry/check-coverage.yaml (the CHK-GATE-*

    obligation registry a new enforced rule id must be registered in) and

    docs/modules/gates.md (rule documentation, required in the same change

    per this repo''s own documentation-as-you-go convention). All of these are

    mechanical, narrow consequences of the EXHAUST001/EXHAUST003 split inside

    the two declared gate modules -- no other behavior in any of these files

    changed.

    '
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/strata/host.md
  reason: 'T-1402: cascade SCOPE002 obligation -- doctor.py/deploy/_conform.py (widened
    for the EXHAUST001 waiver rename) carry frob:doc anchors into these two doc files;
    adding them so the doc-closure check is satisfied, no content in either file is
    touched'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/guides/install.md
  reason: 'T-1402: cascade SCOPE002 obligation -- doctor.py/deploy/_conform.py (widened
    for the EXHAUST001 waiver rename) carry frob:doc anchors into these two doc files;
    adding them so the doc-closure check is satisfied, no content in either file is
    touched'
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_gates.py::TestExhaustiveHandlingGate::test_unresolvable_callee_fires_exhaust003_not_exhaust001
- tests/test_gates.py::TestExhaustiveHandlingGate::test_ambiguous_bare_reraise_still_fires_exhaust001
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_historical_ticket_outside_active_window_is_silent_by_default
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_recent_ticket_outside_old_window_still_fires_exactly_as_today
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_include_history_env_opt_in_restores_the_historical_finding
- tests/test_gates.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001
- tests/test_gates.py::TestExhaustiveHandlingGate::test_catch_all_of_unknown_does_not_fire_exhaust001
designated_repro_test: null
acceptance:
- text: GIVEN an EXHAUST001 finding whose only escape is an unresolvable (Unknown)
    callee WHEN the gate runs THEN it does not demand a catch-all handler under EXHAUST001,
    and any resolution-coverage concern is reported as its own distinct signal
  evidence:
  - tests/test_gates.py::TestExhaustiveHandlingGate::test_unresolvable_callee_fires_exhaust003_not_exhaust001
- text: GIVEN a genuinely unhandled resolvable exception escape WHEN the gate runs
    THEN EXHAUST001 still fires exactly as today, proven by a regression test
  evidence:
  - tests/test_gates.py::TestExhaustiveHandlingGate::test_ambiguous_bare_reraise_still_fires_exhaust001
- text: GIVEN a Done report for a ticket outside the active window WHEN the tickets
    gate runs THEN TICK011 does not fire on it by default
  evidence:
  - tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_historical_ticket_outside_active_window_is_silent_by_default
- text: GIVEN a Done report written now that discloses a cut with no ticket cited
    WHEN the tickets gate runs THEN TICK011 still fires exactly as today, proven by
    a regression test
  evidence:
  - tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_recent_ticket_outside_old_window_still_fires_exactly_as_today
threat: null
component: null
---
Release bar for v1.0.0 is zero errors and zero warnings. A warning count in the thousands means either we were lazy or frob is too noisy. This ticket covers the second cause ONLY, and it is explicitly NOT a licence to delete capability. Every check exists for a reason. The north star stands: if frob passes, the code is good. A rule that is switched off cannot make that guarantee. The goal is to make each rule a precise strike -- fire on the thing it was built to catch, and stay silent otherwise -- so that a zero is honest rather than bought.

Measured on main 2026-08-01 (unwaived counts, from an unscoped frob check):

    TEST005    1444      real work, accuracy pending T-1401
    TICK009      82      self-clearing as tickets close/narrow
    EXHAUST001   69      AIM PROBLEM -- see below
    DOC006       55      real work
    LARGE001     52      real refactors
    TICK011      50      AIM PROBLEM -- see below
    EXHAUST002   37      real work
    COV007       22      real (2 already fixed by dropping needless anchors)
    WALK001/DEAD001/REF002  4/1/1

TARGET 1 -- EXHAUST001, 69 findings, 69 of them (100 percent) citing "(Unknown)".

Every single unwaived EXHAUST001 says an "unresolvable call/raise (Unknown) still escapes" and asks for a catch-all handler. Not one names a concrete exception type that genuinely escapes. So the rule is not reporting "you failed to handle a real error path"; it is reporting "frob's own call-graph could not resolve this callee", and then asking the developer to paper over frob's resolution limit with a broad except.

That is the wrong instrument twice over. It converts a tool limitation into developer work, and the work it asks for -- a catch-all -- makes the code WORSE, since a bare handler hides the very error classes EXHAUST exists to surface. It actively pushes against the north star.

Tune, do not remove: EXHAUST001 should fire when a resolvable call or raise genuinely escapes an incomplete handler set. Where the callee is unresolvable, that is a distinct condition and deserves a distinct, quieter signal (its own rule id, or a diagnostic about resolution coverage) rather than being folded into "you have an unhandled escape". Improving resolution -- native call-graph work, typeshed/stdlib awareness -- converts these into either silence or a real finding. Both outcomes are honest; today's is not.

TARGET 2 -- TICK011, 50 findings, all against historical Done reports in the ledger.

TICK011 flags a Done report that discloses cut/deferred work without citing a follow-up ticket. That check is genuinely valuable AT THE MOMENT A REPORT IS WRITTEN -- it is how disclosed cuts avoid being silently dropped, and it should keep firing there.

But it currently re-scans the entire historical ledger forever, so it fires on reports written long ago, for work whose context is gone: 14 of the 50 cite tickets below T-0500. Retroactively filing follow-ups for years-old cut work is not warranted, and cannot be done honestly -- nobody can now reconstruct what T-0078's "scope cut" referred to. These 50 can never be legitimately driven to zero by doing the work; they can only be waived en masse, which is exactly the dishonest zero we are trying to avoid.

Tune, do not remove: keep full strength on reports for tickets in the active window (or on any report written from now on), and treat the historical tail as closed -- archived, or gated behind an explicit opt-in flag for anyone auditing history deliberately. The capability survives intact for every case where it can still change an outcome.

NOT IN SCOPE, recorded so nobody mistakes them for noise: TEST005's 1444, DOC006's 55, LARGE001's 52, EXHAUST002's 37 and COV007's 22 are real work. They stay. TICK009's 82 clear themselves as tickets close and scopes narrow.

ACCEPTANCE NOTE for whoever implements: do not satisfy this by adding blanket waivers, lowering a threshold, or deleting a rule. The measure of success is that the findings which disappear are ones that were never actionable, and that a deliberately-introduced real violation of each tuned rule is still caught. Prove that with a regression test per rule.