## Done report

The concrete instance at tests/system/test_cli_check.py:237 was already
fixed to kind="e2e" by T-0294. A repo-wide grep for invalid kinds found two
more: kind="drift" in tests/unit/test_strata_tmlanguage.py:13 and
tests/unit/test_extending_guides_complete.py:13 -- both corrected to
kind="unit" (matching T-0294's precedent that a drift-lock conformance test
is a unit test). Valid kinds stay {unit, integration, e2e}; 'system' was NOT
added (T-0225 already decided system/strata ids bind via an e2e-obligation,
not a new sibling kind).

Why these two mattered and why the fix is load-bearing: both directives live
inside MODULE docstrings, so before T-0342 the walker never parsed them at
all -- invisible, not merely malformed. T-0342 (landed in the same commit)
makes docstring directives visible; had these stayed kind="drift" they would
have become surfaced MalformedDirectives that TEST010 escalates to errors.
Correcting them to kind="unit" keeps the tree green and turns them into real
frob:tests edges. Verified empirically: with kind="drift", graph build
reports malformed=1; with kind="unit", malformed=0.

The originally-drafted follow-up (malformed frob:tests beyond frob:waive have
no gate signal) was DROPPED as a false premise: the T-0269 reviewer
confirmed src/frob/gates/__init__.py::_test010_violations (TEST010, T-0237)
already escalates any MalformedDirective whose reason mentions "frob:tests"
-- including a bad kind= -- to an ERROR, mirroring WAIVE001. No new rule
needed.

Evidence: tests/test_graph.py::TestDsl::test_invalid_kind_in_module_docstring_is_surfaced_not_silent
(asserts a bad-kind directive inside a module docstring now surfaces as a
MalformedDirective carrying "frob:tests" in its reason -- no longer a silent
no-op). Landed surgically onto current main.
