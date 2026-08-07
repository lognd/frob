## Done report

Changed:
- src/frob/deploy/__init__.py (new): public surface -- generate_all,
  generate_install_script, generate_status_script,
  generate_uninstall_script, manifest_digest, sorted_manifest_entries,
  DeployDriftViolation, deploy_drift_violations, ManifestEntry.
- src/frob/deploy/_generate.py (new): compiles a merged KernelModel's
  std.host HostManifest facts into deterministic install.sh/status.sh/
  uninstall.sh bash. Install is check-then-apply per step (id -u gate
  for service users, sha256 hash gate for the unit file, stat-compared
  owner/mode gate for owns paths, leading-zero-stripped mode compare so
  "0644" vs "644" never false-positives as drift). Status probes
  systemctl is-active/is-enabled plus /dev/tcp per listens port.
  Uninstall stops+disables+deletes exactly the manifest's own units,
  rm -rf's exactly its own owns paths, userdel's exactly its own
  runs_as users.
- src/frob/deploy/_drift.py (new): DEPLOY001 -- deploy_drift_violations,
  opt-in when deploy/ exists, recompiles from the current design model
  and compares full script bodies against what's committed.
- src/frob/app/deploy_runner.py (new): `frob deploy generate` CLI --
  writes the three scripts, or `--check` verifies without writing.
- src/frob/__main__.py, src/frob/app/config.py, src/frob/app/app.py:
  wired the `deploy` subcommand (Subcommand.deploy, AppConfig deploy_*
  fields, _add_deploy_parser, dispatch table entry) following the `sys`
  subcommand's exact shape.
- src/frob/app/check_runner.py: `_deploy_drift_result` folds DEPLOY001
  into `frob check`'s CheckResult as an extra `deploy-drift` stage
  (NOT wired into frob.gates's pluggable job table -- src/frob/gates/**
  was out of this ticket's declared scope; disclosed below).
- src/frob/strata/_export.py: extracted `node_allowed_syscalls` (public)
  out of `export_seccomp`'s inline may-kind/syscall join so
  `frob.deploy`'s SystemCallFilter= derivation reuses the SAME
  computation instead of a second syscall mapping.
- src/frob/strata/_effects.py: added `node_may_kinds` (public alias of
  `_declared_kinds`) so `frob.deploy`'s CapabilityBoundingSet=
  derivation reuses the same may-kind join `node_allowed_syscalls` uses.
- src/frob/strata/__init__.py: exported both new public symbols.
- docs/commands/deploy.md (new), docs/strata/host.md (added "The deploy
  generator" section + scope-boundary update), docs/index.md (doc-root
  table entry) -- doc coverage for every new public symbol.
- CHANGELOG.md, pyproject.toml: [0.6.0] entry, version bump 0.5.0 ->
  0.6.0 (REL001 flagged this as a minor surface change; judged 0.6.0
  correct given a whole new public package, not a patch-level tweak).
- tests/unit/deploy/test_generate.py, tests/unit/deploy/test_drift.py
  (new), tests/unit/strata/test_export.py, tests/unit/strata/
  test_effects.py, tests/integration/test_interfaces.py: unit coverage
  for every new public symbol plus one end-to-end integration test
  (`frob deploy generate` then `--check`, real CLI subprocess).
- tickets.md: this Done report; evidence recorded via `frob ticket
  evidence`.

Evidence: 15 ids recorded via `frob ticket evidence T-0257`, all
resolved against a fresh `pytest --collect-only` pass (see the
`evidence:` list on this ticket above) -- 8 in test_generate.py, 3 in
test_drift.py, 1 in test_export.py, 2 in test_effects.py, 1 real-CLI
integration test in test_interfaces.py.

Not Filed: T-draft-e20d836a (never refiled) (bug) -- design/frob.strata's self-model has no
`code`/`may` declaration covering the new src/frob/deploy/ tree, so
`tests/unit/strata/test_selfconform.py::TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant` now fails with
SYS102 unmodeled code. `design/frob.strata` was outside this ticket's
declared scope (scope list above), so it was not touched here --
disclosed rather than silently patched around. This does NOT affect
`frob check` itself: `check_self_conformance` is only invoked by `frob
sys audit` and this one dedicated pytest test, never by `frob check`'s
gate set, so `frob check`'s own 0-errors result (below) is unaffected.

Gates: `uv run frob check` (full, not --ticket) after `--stamp-baseline`
and `--stamp-coverage` (post-`make core`, post-`make coverage`): `pass
gates 0 errors, 19 warnings, 223 waived`. Zero DRIFT002. All TEST005
warnings are pre-existing-pattern branch/line-coverage debt (WARN
severity per `[gates.severity]`, matching the repo's existing posture
for that rule), several newly below-threshold in the new deploy files
themselves (`deploy_runner.py` untested via coverage.xml since
subprocess-CLI integration tests do not feed coverage.py) -- not
waived, left as an honest gap for a coverage follow-up rather than
force-padded with low-value unit tests. `git diff main
--diff-filter=D --stat` empty (deletion-filter land rule).
`make core`/`make coverage`'s Cargo.lock churn reverted before every
check and before this report.
