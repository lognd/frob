## Done report

Root cause was fixture rot, not a SYS004 contract regression:

1. `_init_design_repo` never wrote a `pyproject.toml` (or any language
   sentinel), so `detect_project_type` returned "unknown" and CHECK001's
   `_unknown_project_type_result` fired before `frob check` ever reached
   the SYS004 strata stage -- fixed by adding a minimal pyproject.toml.
2. Both fixtures `git init`'d with no explicit branch name; this
   environment's git defaults `init.defaultBranch` to "master", but
   `check_runner`'s diff-driven gates (COV002/PRE001/SCOPE001/TODO001)
   default `base` to "main" when unset -- with no "main" ref/branch in the
   fixture repo, `working_diff` fails to resolve a merge-base and every
   diff-driven gate reports a load error, which for
   `test_check_unaffected_when_no_strata_files` meant a nonzero exit where
   the test expected clean. Fixed by `git init -b main` in both fixtures.
3. `_run_with_faked_missing_native` built its subprocess env from
   `os.environ` unfiltered, so `FROB_AGENT`/`FROB_WORKTREE` (set for every
   dispatched worktree agent, T-0574) leaked into the fixture repo's own
   `frob check` subprocess -- tripping T-0627's "refusing a
   full/unchunked run under FROB_AGENT" guard instead of exercising the
   SYS004 assertion. Reproduced directly: `FROB_AGENT=1 uv run pytest
   tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::
   test_check_fails_loud_with_sys004_when_strata_present` failed before
   the fix, passed after. Fixed by stripping both vars from the child env.

The SYS004 fail-loud contract itself was never broken -- no src/frob/strata
changes were needed.

Overlap with T-0860/T-0725: none of this ticket's own file (tests/system/
test_cli_native_missing.py) touches design/frob.strata or the export
golden fixtures; committed and verified independently, first in the
worktree per the coordinator's suggested order.

Cross-ticket ambiguity found and fixed under T-0860 (not this ticket):
COV002 initially flagged design/frob.strata's mutate/deploy nodes as
uncovered even with T-0860 open and scoped to the file, because T-0845
(another open, unrelated ticket) also declares a literal
"design/frob.strata" scope entry -- a genuine specificity tie per
COV002's own `_scope_covers` tie-break rule. Fixed by adding explicit
`frob:ticket T-0860` directives to both nodes; see T-0860's own commit
and Done report.

Out-of-scope discovery: `frob check --only coverage`/`--only docanchor`
report 5 pre-existing COV001 + 5 DOC002 errors on
src/frob/exports/__init__.py (ConsumerRef/ConsumersResult/
ConsumersResult.as_text/ConsumersResult.as_json/exports_consumers) --
their `frob:doc docs/modules/cli.md#exports-consumers-t-0858` anchor slug
does not match the real anchor spelling
`exports-consumers-surface-t-0858`. Verified via `git log` that this
landed with T-0858 (0c1ed8cf), untouched by any of T-0708/T-0860/T-0725.
Filed as T-0881 rather than fixed silently (out of this
ticket's scope: src/frob/strata/**, tests/system/test_cli_native_missing.py).
This is the ONLY remaining gate error against T-0708 after all fixes; it
is not caused by, or fixable within, this ticket's scope.

Measured: `uv run pytest tests/system/test_cli_native_missing.py -p
no:cacheprovider -q` -> 3 passed (also re-verified with FROB_AGENT=1 set,
reproducing the dispatched-agent environment exactly). `frob check
--ticket T-0708 --only lint` -> 0 errors 0 warnings. `--only static` -> 0
errors, 186 pre-existing warnings (unrelated). `--only gates-native` -> 0
errors. `--only gates-security` -> 0 errors. `--only gates-fast` -> 10
errors before disclosure, all 10 = the 5 COV001 + 5 DOC002
T-0881 findings (0 SCOPE/COV002/PRE001/TODO001 errors of my
own).

### Changed
```
 design/frob.strata                      |   18 +
 tests/golden/frob_export_iam.json       |  210 +++++++
 tests/golden/frob_export_k8s.yaml       |  190 ++++++
 tests/golden/frob_export_seccomp.json   |  117 +++-
 tests/system/test_cli_native_missing.py |   20 +-
 tickets.md                              | 1014 ++++++++++++++++++++++++++++++-
 6 files changed, 1540 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_sys_audit_fails_loud_when_strata_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_fails_loud_with_sys004_when_strata_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
