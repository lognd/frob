## Done report

Added a "May-raise resolver" section to docs/modules/arch.md (anchor
#may-raise-resolver) documenting compute_may_raise, FunctionMayRaise,
UNKNOWN, and UBIQUITOUS_TIER's contracts and this resolver's
relationship to the T-0623 fallibility-checks family (a resolver
computing transitive may-raise sets vs. that family's per-call-site
shape checks). Repointed all four frob:doc directives in
src/frob/arch/_mayraise.py (on UNKNOWN, UBIQUITOUS_TIER,
FunctionMayRaise, and compute_may_raise) from the shared
#fallibility-checks anchor to the new #may-raise-resolver anchor, and
dropped the module-docstring comment referencing T-0916 as a pending
follow-up now that it has landed. No pre-existing frob:waive COV001/
DOC002 was found on _mayraise.py to clear (the ticket's own body notes
these findings were waived pending this ticket, but the file as found
carried no such waiver comment -- verified by grep before starting).

### Changed
- `src/frob/arch/_mayraise.py::UNKNOWN`
- `src/frob/arch/_mayraise.py::UBIQUITOUS_TIER`
- `src/frob/arch/_mayraise.py::FunctionMayRaise`
- `src/frob/arch/_mayraise.py::compute_may_raise`
- `docs/modules/arch.md` (new "May-raise resolver" section, anchor #may-raise-resolver)

### Evidence
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_unresolvable_call_yields_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_reraise_resolves_to_caught_type` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_except_reraise_is_unknown` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_recursive_cycle_converges` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_ambiguous_method_name_across_classes_is_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s)), verified via `uv run pytest tests/unit/test_arch.py::TestMayRaiseResolver -q`
- gates: `uv run frob check --ticket T-0916` -- 0 errors, 2303 warnings, 219 waived
- error-findings: none (measured, zero errors)
