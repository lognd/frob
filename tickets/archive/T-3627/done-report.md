## Done report

Split _mayraise.py's rule tables (UNKNOWN, UBIQUITOUS_TIER,
_EXCEPTION_PARENT, _BUILTIN_RAISERS, _STDLIB_QUALIFIED_RAISERS,
_SUBSCRIPT_RAISE) into a new _mayraise_tables.py module, along the
rule/table boundary the file's own docstring already described.
_mayraise.py imports the moved names; behavior identical. File shrank
from 878 to 756 lines, under the 800-line LARGE001 threshold.
docs/modules/arch.md's may-raise-resolver anchor was repointed
(frob:describes) to the new module for UNKNOWN/UBIQUITOUS_TIER, and
re-verified (frob ack) since their content is unchanged, only their
file location moved.

Evidence: tests/unit/test_arch.py -k mayraise (12 passed, 0 failed) --
existing tests exercising compute_may_raise/FunctionMayRaise/UNKNOWN
re-run against the split code.

Filed: none.

Gates: frob check --ticket T-3627 shows zero LARGE001/ARCH102/ARCH103
findings attributable to this ticket's files (both _mayraise.py and
_mayraise_tables.py). Remaining 13 scoped errors are pre-existing/
out-of-scope: ARCH102 on _lock.py/_land_squash.py (later tickets in
this series), LARGE001 on root-write-guard.py (later ticket in this
series), COV/DEPR/OPAQUE/REL/TEST/WAIVE items in unrelated files.

### Changed
```
 docs/modules/arch.md              |   4 +-
 frob.lock                         |  28 ++++++++
 src/frob/arch/_mayraise.py        | 139 +++--------------------------------
 src/frob/arch/_mayraise_tables.py | 147 ++++++++++++++++++++++++++++++++++++++
 tickets/T-3627/done-report.md     |  42 +++++++++++
 tickets/T-3627/ticket.md          |   5 +-
 6 files changed, 232 insertions(+), 133 deletions(-)
```

### Evidence
- `tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction` (pytest node id, verified passing when recorded)
- `tests/unit/arch_suite/test_guards.py::TestMayRaiseResolver::test_curated_stdlib_c_extension_table_resolves_precisely` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 10 error(s), 4185 warning(s), 901 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
