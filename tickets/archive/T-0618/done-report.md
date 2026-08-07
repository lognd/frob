## Done report

EPIC T-0330's LSP (Liskov) slice of the ARCH1xx catalog. Adds
`frob.arch._solid` with five checks written once against the T-0609
normalized model (`frob.arch._normalized.NormalizedModule`), mirroring
`frob.arch._srp`'s (T-0616) precedent so each check fires identically for
every `LanguageAdapter` with no per-language branch: override raises
NotImplementedError where the base is concrete (ARCH104), override
signature variance -- narrower required params or a differing annotated
return type (ARCH105), override strengthens a precondition via an added
guard-clause raise on a shared param (ARCH106), override weakens a
postcondition by returning nothing where the base always returns a value
(ARCH107), and no-op override of a value-returning base method (ARCH108).

BASE<->OVERRIDE LINKAGE: `NormalizedFunction.overrides` (T-0609) is only
set by adapters with an explicit override keyword (Kotlin/TypeScript/Rust)
-- python's `PythonAdapter` never sets it. Rather than leave python's LSP
checks permanently blind, `_solid.py` resolves the linkage itself,
PRECISION-DISCIPLINE style matching `frob.arch._ocp`'s fail-toward-silence
posture (`_iter_override_pairs`): a class's `bases` are looked up against
every OTHER class in the SAME `NormalizedModule`; a base defined elsewhere
is simply unresolvable and the pair is skipped rather than risked as a
false positive.

Every category stays on the same unwaivable advisory channel every other
`frob.arch` category is on; `symref`/`metric` are populated on every
finding so a future gate-wiring ticket is a gate-side addition, not a
re-instrumentation. `analyze_project` dispatch wiring is explicitly out of
this ticket's scope -- `run_lsp_checks` is the single entry point a future
wiring ticket calls per parsed file, matching T-0616's own disclosed cut
for `run_srp_checks`.

An INV006 (source-level exclusivity-claim vocabulary) finding fired on the
new file's module docstring; reworded one genuinely ambiguous sentence and
added a targeted `frob:waive INV006` for the remaining scope-cut prose,
following the exact precedent `frob.arch._protocol_excuse`'s own module
docstring already carries for the same first-turn-on-pool situation.

### Changed
```
docs/modules/arch.md          | 92 insertions (LSP checks section + top table rows)
src/frob/arch/_models.py      | 10 insertions (5 new ArchCategory values)
src/frob/arch/_solid.py       | 460 lines (new file)
tests/unit/test_arch.py       | 12 new tests across 6 new test classes
```

### Evidence
Collected via `pytest tests/unit/test_arch.py -p no:cacheprovider -q`
(89 passed, full file) and `--collect-only` (all 12 node ids below
resolved):
- tests/unit/test_arch.py::TestOverrideRaisesNotImplemented::test_concrete_override_raising_not_implemented_flagged
- tests/unit/test_arch.py::TestOverrideRaisesNotImplemented::test_base_itself_raising_not_implemented_is_not_flagged
- tests/unit/test_arch.py::TestOverrideSignatureVariance::test_narrower_required_params_flagged
- tests/unit/test_arch.py::TestOverrideSignatureVariance::test_wider_return_type_flagged
- tests/unit/test_arch.py::TestOverrideSignatureVariance::test_same_shape_signature_not_flagged
- tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_added_guard_raise_on_shared_param_flagged
- tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_guard_raise_present_in_base_too_not_flagged
- tests/unit/test_arch.py::TestOverrideWeakenedPostcondition::test_bare_return_where_base_always_returns_value_flagged
- tests/unit/test_arch.py::TestOverrideWeakenedPostcondition::test_override_also_always_returning_value_not_flagged
- tests/unit/test_arch.py::TestNoOpOverride::test_empty_body_override_of_value_returning_base_flagged
- tests/unit/test_arch.py::TestNoOpOverride::test_override_with_real_body_not_flagged
- tests/unit/test_arch.py::TestRunLspChecks::test_combines_multiple_checks

`frob check --only lint/static/gates-fast/gates-native/gates-security
--ticket T-0618` (chunked loop): all five stage groups 0 errors after the
INV006 fix and a `git merge main` (which also independently resolved a
pre-existing DRIFT002/TICK006 pair that had moved on main mid-session,
unrelated to this ticket's scope).

### Filed
none -- no out-of-scope work discovered.

### Gates
`frob check --only <lint|static|gates-fast|gates-native|gates-security>
--ticket T-0618` clean (0 errors each, measured individually after the
final `git merge main`). `static`'s pre-existing repo-wide dup-block
warnings are unrelated to this ticket's files. `frob.arch.__init__`
does not import/export `_solid`'s new public symbols (a warning, not an
error, EXPORTS gate) -- matching T-0616's own precedent of leaving
`_srp.py` unexported until the separate T-0728 wiring ticket; wiring
`_solid.py` into `analyze_project`/`__init__.py`/a real ARCH1xx gate is
out of this ticket's declared scope, same disclosed cut.

### Changed
```
 docs/modules/arch.md     | 101 +++++++++
 src/frob/arch/_models.py |  11 +
 src/frob/arch/_solid.py  | 466 ++++++++++++++++++++++++++++++++++++++
 tests/unit/test_arch.py  | 572 +++++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 1150 insertions(+)
```

### Evidence
- `tests/unit/test_arch.py::TestOverrideRaisesNotImplemented::test_concrete_override_raising_not_implemented_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideRaisesNotImplemented::test_base_itself_raising_not_implemented_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideSignatureVariance::test_narrower_required_params_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideSignatureVariance::test_wider_return_type_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideSignatureVariance::test_same_shape_signature_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_added_guard_raise_on_shared_param_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition::test_guard_raise_present_in_base_too_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideWeakenedPostcondition::test_bare_return_where_base_always_returns_value_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestOverrideWeakenedPostcondition::test_override_also_always_returning_value_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNoOpOverride::test_empty_body_override_of_value_returning_base_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestNoOpOverride::test_override_with_real_body_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRunLspChecks::test_combines_multiple_checks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
