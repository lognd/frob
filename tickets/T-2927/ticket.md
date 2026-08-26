---
id: T-2927
title: 'frob-suggest: add missing must-stay-quiet fixtures for 5 rules'
state: done
kind: docs
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_hook_frob_suggest.py::test_make_target_still_fires_at_command_position
- tests/test_hook_frob_suggest.py::test_make_target_stays_quiet_as_prose_in_a_commit_message
- tests/test_hook_frob_suggest.py::test_raw_linters_still_fires_at_command_position
- tests/test_hook_frob_suggest.py::test_raw_linters_stays_quiet_as_prose_in_a_commit_message
- tests/test_hook_frob_suggest.py::test_raw_coverage_still_fires_at_command_position
- tests/test_hook_frob_suggest.py::test_raw_coverage_stays_quiet_as_prose_in_a_commit_message
- tests/test_hook_frob_suggest.py::test_unscoped_pytest_still_fires_bare
- tests/test_hook_frob_suggest.py::test_unscoped_pytest_stays_quiet_when_a_path_is_given
- tests/test_hook_frob_suggest.py::test_unscoped_symbol_search_still_fires_bare
- tests/test_hook_frob_suggest.py::test_unscoped_symbol_search_stays_quiet_with_dash_dash_path
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob-suggest.py audit (T-2908) found these rules still lack a must-stay-quiet
fixture in tests/test_hook_frob_suggest.py, with no demonstrated false
positive to fix alongside:

- make-target: no plausible false positive found (a `make <target>` at
  command position is always the discouraged case); worth a quiet-case test
  anyway for regression coverage (e.g. a prose mention of "make" that is not
  at command position).
- raw-linters (ruff/mypy/ty check|format): scoping to a single file does not
  change the intended behavior (frob check should still own gate accounting),
  so no false positive found; still lacks any must-stay-quiet fixture.
- raw-coverage (coverage run / pytest --cov): same as above -- section 6b of
  the playbook explicitly forbids agent-run coverage regardless of scope, so
  no false positive found; still lacks a must-stay-quiet fixture.
- unscoped-pytest: HAS a working negative pattern (path/node-id/`.py`
  anywhere in the raw command) but zero test exercises the quiet path.
- unscoped-symbol-search (git grep): HAS a working negative pattern
  (`-- <path>`) but zero test exercises the quiet path directly (only an
  incidental assertion inside a different rule's test).

None of these need a functional fix as far as this audit could demonstrate;
they need must-stay-quiet regression tests added so a future edit to the
rule/pattern cannot silently regress into a T-2908-shaped misfire again.