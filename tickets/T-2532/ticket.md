---
id: T-2532
title: WIRE001 reach scan misses dotted classmethod/staticmethod calls
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- src/frob/strata/_multifile.py
evidence_scope:
- tests/unit/test_wire001_dotted_method_call.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/_multifile.py
  reason: WIRE001's fix in this same ticket makes this file's now-stale waiver for
    the exact incident (SealedGrantSet.from_root_node) obsolete; the registry's live-tracker
    citation blocks close unless it is re-pointed here
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_genuinely_unwired_method_still_flagged
- tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_similarly_named_dotted_call_does_not_false_positive_reach
designated_repro_test: tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged
acceptance:
- text: given a genuine classmethod/staticmethod called only dotted-qualified (ClassName.method(...)
    or instance.method(...)), when WIRE001's reach scan runs, then it is not flagged
    as unreached
  evidence:
  - tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_classmethod_called_dotted_qualified_is_not_flagged
- text: given a method with no caller anywhere, bare or dotted-qualified, when WIRE001's
    reach scan runs, then it still fires
  evidence:
  - tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_genuinely_unwired_method_still_flagged
  - tests/unit/test_wire001_dotted_method_call.py::TestWireGateDottedMethodReach::test_similarly_named_dotted_call_does_not_false_positive_reach
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: daf301da110e830393b78564e35761d249e48adf
---
_wire.py::_wire_reach_patterns's call_pattern regex is
(?<![A-Za-z0-9_.]){short}\s*\( -- the negative lookbehind explicitly
excludes any match preceded by a dot, so a legitimate real call site
shaped ClassName.method_name(...) (a classmethod/staticmethod called
qualified, the only way Python lets you call one) is invisible to
WIRE001's reach scan. member_access_pattern (the short.attr CLASS
shape) does not help either since it only fires for SymbolKind.CLASS
records, not for the METHOD symbol itself.

Discovered in T-2530: SealedGrantSet.from_root_node is a real
classmethod, called exactly once (its only sanctioned call site,
intentionally) as SealedGrantSet.from_root_node(node) from
_seed_grants_by_root_node in the same file -- a genuine, working,
non-test caller -- and WIRE001 still flagged it as unreached, forcing a
frob:waive for code that is not actually unwired.

Fix: extend call_pattern (or add a sibling regex, METHOD/staticmethod
kind only) to also match a dotted-qualified call
(?:[A-Za-z_][A-Za-z0-9_]*\.)+{short}\s*\( so a real
ClassName.method(...) call site counts as reached, the same way
wrapper_pattern already allows an optional name.-qualified prefix for
its dict-table-value shape.