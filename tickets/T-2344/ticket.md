---
id: T-2344
title: 'meta-check: a gate rule constructed from raw text without symref/AST binding
  must itself be a finding'
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- src/frob/gates/_lexical_selfcheck.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/gates/_wire.py
- src/frob/check/__init__.py
- tests/unit/gates/test_lexical_selfcheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: too broad -- collided with T-1606 and every other test-touching ticket;
    narrow to a single new test file once implementation starts
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/gates/**
  reason: 'narrow: new standalone meta-check module + its wiring into __init__.py''s
    gate registry, not every existing gates/** file'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/_lexical_selfcheck.py
  reason: 'narrow: new standalone meta-check module + its wiring into __init__.py''s
    gate registry, not every existing gates/** file'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'narrow: new standalone meta-check module + its wiring into __init__.py''s
    gate registry, not every existing gates/** file'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/_waive.py
  reason: register the new LEXCHECK001 rule id in _KNOWN_GATE_RULES, same drift-lock
    convention every other new rule id follows
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/_wire.py
  reason: add frob:waive LEXCHECK001 above _wire001_cli_dest_violations, citing the
    new T-2348 follow-up, so the new gate ships clean
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/check/__init__.py
  reason: register the new lexcheck gate name in _STAGE_GROUPS's gates-fast set --
    same 'omission means unreachable via --only <group>' bug class already fixed once
    for ffi_boundary/suppress
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/gates/test_lexical_selfcheck.py
  reason: evidence file for the new gate
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_new_lexical_decider_is_flagged
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_allowlisted_function_is_silent
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_semantic_function_with_incidental_regex_is_silent
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_non_gate_code_never_scanned
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_gates_module_module_stays_clean
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1662's own directive #4 asks for a meta-check: "a new gate rule
constructed from raw text without a symref or AST node should itself be
a finding, so this class cannot silently return." T-1663's classification
pass (docs/design/gate-semantics-classification.md) enumerated every
existing (c)-class defect and its addendum caught two MORE that surfaced
after the initial survey (T-2178, the callgraph substrate/T-2201) --
directly demonstrating the class can and does recur. All currently-known
instances are now fixed (T-1665, T-2178, T-2187, T-2188, T-2201, T-2243),
but nothing stops a SIXTH one from landing tomorrow the same way the first
five did, each discovered only by a human-initiated audit.

This ticket is the meta-check itself, not another instance fix:

Add a gate (or a `frob check` self-audit pass, mirroring SELFAUDIT001's
own "does this repo's tooling obey its own rules" shape) that inspects
every gate rule's OWN implementation and flags one whose `Violation`
construction:
  - never attaches a `symref`/AST node reference, AND
  - is reachable from a `re.search`/`re.match`/`re.findall`/`.startswith`/
    `.endswith` call over raw source TEXT (not tool-output text, not a
    ticket-ledger/DSL-comment text, both of which are legitimately
    textual per docs/design/gate-semantics-classification.md's class
    (b))

Design questions to resolve at implementation time (do not guess in this
ticket's own body -- read the file first per this drive's own repeated
lesson):
  - Whether this is itself a static AST check over src/frob/gates/**
    (finds the pattern once, at `frob check` time, cheap) or a runtime
    Violation-shape check (only fires when a rule actually emits a
    symref-less Violation from a text-decided code path -- more
    precise, more expensive, requires threading provenance through
    Violation construction).
  - How to encode the class-(b) exemption list (SEC001-004, EXCL001,
    fmt's directive wrap, `_rule_id_scan.py`'s own generator,
    TICK011's phrase-scan, WAIVE004's parsing half) so a legitimately
    textual rule is not itself flagged -- reuse
    docs/design/gate-semantics-classification.md's own table as the
    source of truth rather than inventing a second list.

Positive control this needs: a deliberately reintroduced lexical-decision
rule (e.g. a scratch gate module written specifically for the test,
matching REF001's pre-T-1665 shape) that the new meta-check MUST flag,
proving it actually fires and is not a check that always reports "nothing
found" the way every incident in this epic's own history did.

Scope should stay narrow: the new meta-check module/gate, its test file,
and docs/modules/gates.md's rule catalog entry -- do not touch the
individual gate modules this ticket is auditing.