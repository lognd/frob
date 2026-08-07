---
id: T-1485
title: 'perf: fold arch nesting/cyclomatic/events into one walk; consolidate _walk_all/_find_if_statements'
state: done
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- src/frob/arch/_concurrency_model.py
- src/frob/arch/_patterns.py
- src/frob/arch/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/__init__.py
  reason: the _find_if_statements triplicate-walk this ticket's own brief names (T-0332's
    own design note calling out iter_type_switch_chains/_check_state_field_chain/_check_stringly_typed
    as 3 independent consumers) can only be de-duplicated at their actual call site,
    which lives in arch/__init__.py's per-file suggestion loop, not inside _patterns.py
    itself
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_arch.py::TestPatternRecommender::test_isinstance_chain_recommends_strategy
- tests/unit/test_arch.py::TestPatternRecommender::test_state_field_chain_recommends_state_machine
- tests/unit/test_arch.py::TestPatternRecommender::test_stringly_typed_recommends_newtype
- tests/unit/test_arch_ocp.py::TestTypeDispatchSmell::test_isinstance_chain_flags_ocp_violation
designated_repro_test: null
threat: null
component: null
---
T-1215 fixed the _iter_own_scope quadruplication (lock_ordering,
async_hazards, shared_state_race, concurrency_model all now share
frob.arch._python._iter_own_scope). The OTHER half of report candidate #9
is not done: arch/_python.py's _py_build_module/_py_build_function still
run nesting/cyclomatic/events as 3 separate recursions per function
instead of folding them into the existing _py_collect_body_events walk,
and _concurrency_model.py's _walk_all plus _patterns.py's
_find_if_statements are further independent per-file walks not yet
consolidated.

This was deliberately NOT attempted in T-1215: _py_build_function's own
docstring explicitly documents that max_nesting_depth/cyclomatic are kept
as SEPARATE walks rather than derived from the flattened event list "so
these two metrics match the original per-language walk exactly,
byte-for-byte" -- collapsing them risks silently changing either metric's
value for edge cases (e.g. node types counted by _py_max_nesting/
_py_cyclomatic that _py_collect_body_events does not visit the same way).
That merge needs its own careful pass with a byte-identical-output proof
across a real corpus, not a quick fold-in inside a multi-ticket sweep.

Scope for the follow-up: src/frob/arch/_python.py (nesting/cyclomatic/
events fold), src/frob/arch/_concurrency_model.py (_walk_all), src/frob/
arch/_patterns.py (_find_if_statements).