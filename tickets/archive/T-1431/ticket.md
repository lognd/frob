---
id: T-1431
title: WIRE001 fires on relocated symbols, so every file split trips it
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged
- tests/test_gates.py::TestWireGate::test_genuinely_new_symbol_in_a_split_sibling_file_is_still_flagged
designated_repro_test: null
acceptance:
- text: GIVEN a diff that relocates a symbol into a new file without changing its
    reachability WHEN the wire gate runs THEN WIRE001 does not fire for that symbol
  evidence:
  - tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged
- text: GIVEN a diff that introduces a genuinely new symbol with no caller WHEN the
    wire gate runs THEN WIRE001 still fires exactly as today, proven by a regression
    test
  evidence:
  - tests/test_gates.py::TestWireGate::test_genuinely_new_symbol_in_a_split_sibling_file_is_still_flagged
threat: null
component: null
---
WIRE001 (T-1428) fires on symbols a diff RELOCATES, not just symbols it introduces, because a file split makes every moved symbol look new to a diff-scoped analysis.

First real-world encounter, measured 2026-08-02 on T-1420's split of src/frob/vet/_capability_registry.py into a package:

  WIRE001: _matrix.py::_unexcused_empty_cells is new in this diff and has no caller outside its own module
  WIRE001: _matrix.py::_validate_registry_kinds  ... same

Both judgements are correct about the CODE: each is called only from tests/test_capability_registry.py, with no production caller. But neither is new. Both existed in the pre-split single file with exactly the same test-only status, and the split moved them verbatim. Nothing about the ticket's change made them less reachable.

WHY THIS MATTERS MORE THAN TWO FINDINGS. Every LARGE001 file split creates new files full of relocated symbols, so WIRE001 will fire on every one of them. There are 50 such files left, and the splits are exactly the work the v1.0.0 zero-warning bar needs. A rule that blocks the refactors it should be neutral about will get waived reflexively, and a reflexively-waived rule stops catching the real thing -- which for WIRE001 is the seven-instance inert-code class it was built for.

THE FIX. Compare against the SYMBOL's prior existence, not the FILE's. A symbol whose fully-qualified name (or whose body, by digest) existed anywhere in the tree at the merge base is relocated, not introduced, and WIRE001 should stay silent about its reachability. Only a genuinely new symbol -- one with no prior existence under any path -- is in scope. The graph already computes per-symbol digests, so the information needed is present.

Two sub-cases worth handling deliberately rather than by accident: a symbol that is relocated AND changed in the same diff (still relocated -- the reachability question is unchanged unless the change is what removed its caller), and a symbol relocated into a file that also introduces genuinely new symbols (the new ones stay in scope).

NOT IN SCOPE, and worth stating so it is not lost: the two findings above ARE real, pre-existing, test-only production symbols. Making WIRE001 relocation-aware does not make them reachable. They are a legitimate DEAD-family question about test-only helpers living in production modules, and if that is worth acting on it deserves its own ticket rather than being smuggled in here.