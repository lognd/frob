---
id: T-1659
title: Audit CACHE001/OPAQUE001 (and PERF/PII/SEC005) for the DEAD001-class missing-symref
  waiver hole
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_cache_gate.py
- src/frob/gates/_opaque.py
- tests/test_vet.py
- tests/test_cache_gate.py
- src/frob/gates/_waive.py
- frob.lock
- src/frob/logging/filter.py
- src/frob/vet/_capability_scan.py
- src/frob/app/_config_external.py
- tests/unit/test_dup_core.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet.py
  reason: frob:tests directives on the fixed symbols point at these test files; SCOPE002
    requires them in the ticket's declared scope
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_cache_gate.py
  reason: frob:tests directives on the fixed symbols point at these test files; SCOPE002
    requires them in the ticket's declared scope
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/gates/_waive.py
  reason: src/frob/gates/_waive.py::_apply_waivers is exercised directly by this ticket's
    own new waiver-scoping test; frob.lock was updated by 'frob ack' after this ticket's
    opaque_gate body digest changed
  actor: logan
  at: '2026-08-06'
- op: add
  glob: frob.lock
  reason: src/frob/gates/_waive.py::_apply_waivers is exercised directly by this ticket's
    own new waiver-scoping test; frob.lock was updated by 'frob ack' after this ticket's
    opaque_gate body digest changed
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/logging/filter.py
  reason: 'T-1659 semantic-check follow-up per coordinator directive: OPAQUE001''s
    needle scan itself needed an AST-based bare-call check (src/frob/vet/_capability_scan.py),
    and src/frob/logging/filter.py needed its existing waiver comment relocated around
    the _enclosing_src mis-binding bug so main can land at 0 errors'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: 'T-1659 semantic-check follow-up per coordinator directive: OPAQUE001''s
    needle scan itself needed an AST-based bare-call check (src/frob/vet/_capability_scan.py),
    and src/frob/logging/filter.py needed its existing waiver comment relocated around
    the _enclosing_src mis-binding bug so main can land at 0 errors'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-1659 semantic-check follow-up: symref narrowing means the pre-existing
    multi-function OPAQUE001 waiver above _apply_string_fields no longer covers its
    5 sibling _apply_*_fields helpers; each now needs its own copy of the same reasoning'
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_dup_core.py
  reason: 'T-1659 semantic-check follow-up: one genuine (not scanner-bug) OPAQUE001
    finding remains after the AST fix -- a closed-tuple getattr(frob_core, name) test
    assertion needs its own waiver'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_waiver_scoped_to_symbol_not_whole_file
- tests/test_cache_gate.py::TestCache001Symref::test_violation_carries_symref
- tests/test_vet.py::TestOpaqueIndirectionGate::test_dotted_setattr_call_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_dotted_eval_method_call_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_identifier_ending_in_builtin_name_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_bare_setattr_call_still_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_sys_modules_read_does_not_fire
- tests/test_vet.py::TestOpaqueIndirectionGate::test_sys_modules_write_still_fires
designated_repro_test: null
acceptance:
- text: CACHE001 and OPAQUE001 Violations carry symref; waiver matching re-verified
    against the new symref for OPAQUE001's existing 166-waiver population
  evidence:
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_violation_carries_symref
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_waiver_scoped_to_symbol_not_whole_file
  - tests/test_cache_gate.py::TestCache001Symref::test_violation_carries_symref
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_dotted_setattr_call_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_dotted_eval_method_call_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_identifier_ending_in_builtin_name_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_bare_setattr_call_still_fires
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_sys_modules_read_does_not_fire
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_sys_modules_write_still_fires
threat: null
component: null
---
T-1652 fixed dead_symbol_gate never setting Violation.symref, which let
frob:waive DEAD001 fall back to file-scope matching and silently
over-forgive every DEAD001 finding in a waived file (44 of 62 findings
mis-waived by one directive). Auditing sibling gates for the same
"per-symbol finding constructed without symref" shape (requested by the
T-1652 aftermath review, T-1658's dispatch brief) surfaced two
live candidates, both currently ERROR-tier and both carrying real waiver
populations today:

- CACHE001 (src/frob/gates/_cache_gate.py, _cache001_violation): the
  finding is inherently per-@memoize_per_run-function (site.func_name is
  already resolved and used in the message text) but Violation() never
  passes symref=f"{rel_path}::{site.func_name}". No live CACHE001 waiver
  exists yet, so this is a dormant hole, not an active over-forgiveness --
  but the first frob:waive CACHE001 written in a file with more than one
  @memoize_per_run function will silently forgive all of them, the exact
  DEAD001 shape.
- OPAQUE001 (src/frob/gates/_opaque.py, opaque_gate): promoted to ERROR
  (T-1185) and currently carries 166 live waived findings repo-wide --
  the largest waived population of any rule in the tree after this
  ticket's DEAD001 cleanup. finding.construct_name/finding.rationale are
  resolved per-site by frob.vet._capability._opaque_indirection_findings
  but Violation() never sets symref, so every OPAQUE001 waiver in the
  tree is running on file-scope matching right now, unverified. Given the
  size of the waived population this is the single highest-value
  candidate to re-audit once symref is wired, mirroring exactly what
  T-1652's DEAD001 fix uncovered (44/62 mis-waived).

Not investigated in depth (time-boxed out of the audit that filed this
ticket): PERF001-014 (4 of 19 files under src/frob/perf/ set symref
today, rest unchecked), PII011/PII012 (src/frob/gates/_pii_structural/*,
2 of 5 violation-emitting files set symref today), SEC005/taint_gate
(src/frob/gates/_taint_gate.py, no symref at all, per-sink finding).
Recommend a first pass on CACHE001 and OPAQUE001 (highest confidence,
highest stakes given OPAQUE001's waived population), then sweep the rest.