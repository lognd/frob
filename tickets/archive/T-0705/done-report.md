## Done report

Chosen contract: graceful degradation, matching `ref_gate`/DOC004's
existing posture exactly. `secrets_gate`/`pii_structural_gate`/
`render_lint_gate`/`walk_lint_gate` already returned `()` (no candidates,
no violations) on a `git ls-files` failure -- the only inconsistency was
logging that condition at ERROR instead of WARNING, painting the gate's
line red in `frob check`'s raw log stream for a target that was never a
real violation. Fixed by changing `_log.error` to `_log.warning` in all
four gates' tracked-file resolvers (`_secrets._tracked_files`,
`_pii_structural._tracked_python_files`, `_render_lint.
_tracked_python_files`, `_walk_lint._tracked_python_files`), with an
updated docstring on each explaining the T-0705 rationale. Documented the
consistent contract in docs/modules/gates.md under a new
"Git-less target contract T-0705" section (anchor
`git-less-target-contract-t-0705`), including why git-as-hard-requirement
was rejected (frob check/ticket new both already document accepting a
plain filesystem path) and explicitly noting COV002/SCOPE001/TODO001's
diff-load-failure mechanism (T-0550) is a distinct, deliberate concern
this ticket does not touch.

Investigation finding (see Filed below): most of the ~12 originally-
reported failures in tests/system/test_cli_check.py are NOT actually
caused by the four named gates' ERROR/WARNING log level at all -- those
four gates already returned zero violations either way, so their log
level never affected `frob check`'s exit code or violation summary in any
observed test. The dominant root cause across ~7 of the 9 still-failing
tests in test_cli_check.py is COV002/SCOPE001/TODO001 (`_load_diff`'s
diff_load_failed hard-error, T-0550) firing because the fixture has no
git repo at all (not because a real diff genuinely failed) -- this
mechanism lives in src/frob/gitio.py (out of T-0705's declared scope) and
gates/__init__.py's diff-load classification (a distinct, deliberately-
designed T-0550 concern I did not touch without ticket authorization).
Two remaining test_cli_check.py failures plus test_cli_perf.py's one
failure are CHECK001 "unknown project type: 'unknown'" -- unrelated to
git entirely (fixtures missing pyproject.toml), also out of T-0705's
scope (src/frob/app/**).

Before/after on the two named files (measured, `-k "not
StampBaselineAndDelta"` deselected on test_cli_check.py per the known
T-0581 deadlock hazard -- never run, not counted either direction):

- tests/system/test_cli_check.py: 10 failures before -> 9 failures after
  (test_pinned_check_type_reports_skipped_line now passes; it was purely
  driven by the four gates' ERROR noise with no COV002/SCOPE/TODO
  involvement). Plus 2 new regression tests added (both pass).
- tests/system/test_cli_perf.py: 1 failure before -> 1 failure after
  (unchanged; that single failure is the CHECK001 unknown-project-type
  bug, unrelated to this ticket's mechanism).

Deadlocked tests: none directly hit -- `TestCheckStampBaselineAndDelta` in
test_cli_check.py was deselected proactively per the playbook's known
T-0581 hazard and never executed in this session.

Filed for the remainder (both out-of-scope for T-0705, scope glob would
require touching src/frob/gitio.py and src/frob/app/**):
- T-draft-85590807: COV002/SCOPE001/TODO001 hard-error on a genuinely
  git-less root vs. a real repo's bad diff (T-0550 mechanism).
- T-draft-3a81a23d: CHECK001 "unknown project type" on fixtures missing
  pyproject.toml, unrelated to git.

### Changed
```
 tickets.md | 306 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 303 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root` (pytest node id, verified passing when recorded)
