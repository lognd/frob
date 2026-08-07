## Done report

Changed:
- `src/frob/strata/_audit.py::evaluate_exhaustiveness` -- folds HOST001/
  HOST002 (via `_host_isolation.py::evaluate_host_isolation_waived`) and a
  new auto-generated per-`runs_as`-user compromised-user blast-radius
  scenario (via `_scenarios.py::build_compromised_user_scenario` +
  `evaluate_scenarios`, mirroring `_crash.py::_generate_crash_scenarios`'s
  auto-generation shape) into the exhaustiveness conjunction `frob sys
  audit` already dispatches to (`src/frob/app/sys_runner.py::_run_audit`
  was unchanged -- it already called `evaluate_exhaustiveness`, so this
  was the entire CLI-reachability gap).
- `src/frob/strata/_audit.py::_host_isolation_gap` (new, private) --
  adapts `HostIsolationViolation` into `FamilyGap` under
  family="host"/view="model", mirroring `_lint_gaps`/`_pii_gaps`.
- `src/frob/strata/_audit.py::_blast_radius_gaps` (new, private) --
  adapts a compromised-user scenario's REFUTED claims into `FamilyGap`s
  (rule="HOST-BLAST") under view="blast-radius".
- `src/frob/strata/_audit.py::_HOST_RULE_IDS` (new, private constant) --
  excludes HOST001/HOST002 from the module's OWN generic `apply_waivers`
  pass, since `evaluate_host_isolation_waived` already runs those two
  rule ids through their own waiver channel (mirrors how SYS100-102 are
  excluded for `check_self_conformance`) -- without this exclusion, an
  already-matched HOST waiver would be misreported STALE a second time.
- `docs/strata/host.md` -- new "CLI reachability (T-0280)" subsection
  under "Movement-impossibility proofs" documenting the wiring.
- `tests/unit/strata/test_audit.py::TestHostWiring` (new class, 3 tests)
  -- `test_shared_model_gaps`, `test_hardened_model_proved`,
  `test_no_runs_as_no_gaps`, exercising `evaluate_exhaustiveness` directly
  against the shared-writable/hardened-waived/no-runs_as fixture shapes.
- `tests/system/test_system.py` -- 2 new subprocess-level system tests:
  `test_sys_audit_shared_writable_two_user_model_exits_nonzero_with_host001`
  and `test_sys_audit_hardened_waived_two_user_model_proved`, driving the
  REAL `frob sys audit <dir>` CLI entrypoint against a minimal tmp_path
  repo (own `frob.toml` + `design/*.strata`) -- proves acceptance
  criterion 3 (CLI-level, not a hand-written harness).

Evidence (all collected via `uv run pytest --collect-only -q -o addopts=`):
- `tests/unit/strata/test_audit.py::TestHostWiring::test_shared_model_gaps`
- `tests/unit/strata/test_audit.py::TestHostWiring::test_hardened_model_proved`
- `tests/unit/strata/test_audit.py::TestHostWiring::test_no_runs_as_no_gaps`
- `tests/system/test_system.py::test_sys_audit_shared_writable_two_user_model_exits_nonzero_with_host001`
- `tests/system/test_system.py::test_sys_audit_hardened_waived_two_user_model_proved`
- Full targeted run (`uv run pytest tests/unit/strata/test_audit.py
  tests/unit/strata/test_host_isolation.py
  tests/unit/strata/test_litmus_host_isolation.py
  tests/unit/strata/test_scenarios.py tests/system/test_system.py -q`):
  79 passed, 0 failed.
- `TestRealGateGreen` (`uv run pytest -q -k TestRealGateGreen`): 1 passed.

CLI-level proof (real `frob sys audit` subprocess, not a harness) --
2-user model with `owns "/var/lib/shared"` shared between `runs_as
"svc-a"`/`runs_as "svc-b"`:
```
$ uv run frob sys audit <repo-with-shared-writable-2-user-model>
ERROR: sys audit: GAP family=host view=model rule=HOST001 detail=users 'svc-a' and 'svc-b' both own writable path '/var/lib/shared' -- a compromise of either reaches the other's data
$ echo $?
1
```
Hardened/waived twin (disjoint paths + `waive "HOST001:shared-group"` /
`waive "HOST002:sudoers"`): `uv run frob sys audit <repo>` exits 0,
`sys audit: PROVED (3 waived) -- zero UNWAIVED gaps across every
configured view`.

No-regression check on `design/frob.strata` (the repo's own self-audit
model, 0 `runs_as` declared): `uv run frob sys audit .` exits 0,
`host_isolation: HOST001 skipped -- 0 runs_as user(s) declared, need 2+`
/ `HOST002 skipped -- no runs_as users declared`, `sys audit: PROVED (5
waived) -- zero UNWAIVED gaps across every configured view` -- identical
to pre-change behavior, confirming zero regression for models outside
T-0280's scope.

Filed: none (no out-of-scope discovery this pass).

Gates: `uv run frob check` (natives built via `make core` in this
worktree) -- `## Tool summary`: `ruff-check` no issues, `ruff-format` all
files formatted, `ty` no issues, `frob-cycle` no cycles, `gates` 0 errors,
6 warnings, 27 waived (all pre-existing PERF00x waivers, none new). 0
`DRIFT002` occurrences in the check output. Deletion filter
(`git diff main --diff-filter=D --stat`) is empty -- no unintended
deletions outside scope.

Not closing per the ticket workflow (review-gated) -- leaving for the
reviewer/coordinator to close.
