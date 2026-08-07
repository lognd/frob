## Done report

Changed: src/frob/arch/_mayraise.py (new: compute_may_raise/FunctionMayRaise/UNKNOWN/UBIQUITOUS_TIER), src/frob/arch/_normalized.py (NormalizedSubscript + NormalizedFunction.subscripts), src/frob/arch/_python.py (PythonAdapter subscript-node collection), tests/unit/test_arch.py (TestMayRaiseResolver, 6 tests)

Evidence: tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction, tests/unit/test_arch.py::TestMayRaiseResolver::test_unresolvable_call_yields_unknown, tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_reraise_resolves_to_caught_type, tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_except_reraise_is_unknown, tests/unit/test_arch.py::TestMayRaiseResolver::test_recursive_cycle_converges, tests/unit/test_arch.py::TestMayRaiseResolver::test_ambiguous_method_name_across_classes_is_unresolved -- all verified passing (`uv run pytest -q tests/unit/test_arch.py::TestMayRaiseResolver`: 6 passed; full `tests/unit/test_arch.py` suite passing; `uv run frob test --base main`: PASS exit=0)

Filed: T-0916 (docs: document the may-raise resolver in docs/modules/arch.md -- out of T-0686's declared scope; _mayraise.py's frob:doc directives point at the existing #fallibility-checks anchor in the meantime)

Gates: `uv run frob check --ticket T-0686 --only gates-fast` clean (0 errors), `--only gates-native` clean, `--only gates-security` clean, `--only lint` clean, `--only static` clean; `uv run ty check` and `uv run ruff check`/`ruff format` clean on all touched files
