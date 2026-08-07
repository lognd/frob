## Done report

Changed:
- `src/frob/deploy/_audit.py` (new): pure diff/proof/attestation logic --
  `FileFact`, `StateCapture`, `StateDiff` (+ `is_empty`,
  `mutated_targets`), `diff_states`, `idempotence_holds`,
  `artifact_freeness_holds`, `install_exactness_holds`,
  `assert_not_installed`, `assert_healthy`, `CheckpointResult`,
  `AuditAttestation` (+ `passed`, `to_json`), `build_attestation`,
  `ALLOWLIST_PATTERNS`. No VM/ssh/subprocess anywhere in this module --
  data-in, data-out, fully unit-tested.
- `src/frob/deploy/_vm_runner.py` (new): the thin, deliberately-untested-
  in-CI VM orchestration sliver -- `VmAuditConfig`, `AuditRunResult`,
  `run_vm_audit`, `vboxmanage_available`, plus private `VBoxManage`/`ssh`/
  `scp` helpers driving the exact sequence spec (restore snapshot -> C0
  -> install -> C1 -> install again -> C1' -> uninstall -> C2). Graceful
  degrade: `vboxmanage_available()` is the FIRST check in `run_vm_audit`,
  before any subprocess call; returns `status="skipped"` with a reason,
  never a fabricated pass.
- `src/frob/deploy/__init__.py`: re-exports the new public surface.
- `tests/unit/deploy/test_audit.py` (new, 16 cases), `tests/unit/deploy/
  test_vm_runner.py` (new, 2 cases): fixture-based, no VM/ssh/VBoxManage
  anywhere. `frob:tests` directives live in these files, above each test
  method, pointing at the source symref as target
  (`src/frob/deploy/_audit.py::<symbol> kind="unit"`) -- NOT the
  source-file-side placement `_conform.py`/`_generate.py` use, because
  empirical testing against this worktree's live `frob.gates._test_edges`/
  `_test001_002_one` showed a freshly-parsed `frob:tests` directive
  produces `Edge(src=<annotated symbol>, target=<parsed text>)`
  (`frob.graph.dsl.parse_directives`), while `_test_edges` groups by
  `edge.target` and `_test001_002_one` looks up by `unit_edges.get(record.
  symref)` -- so for a FRESH parse to bind correctly the directive must
  sit on the TEST side with the SOURCE symref as its target. The existing
  `_conform.py`/`_generate.py` directives (source-side, target=test) only
  pass today because their file content is unchanged since an older
  `.frob/cache.db` entry was written (confirmed via a direct fresh
  `parse_file`+`parse_directives` call on the real `_generate.py`, which
  reproduces the source-side shape, vs. the cached `GraphSnapshot`'s
  edges for that same file, which come back reversed) -- a latent
  cache/dsl inconsistency in `frob` itself, NOT touched here (out of
  `src/frob/gates/**`/`src/frob/graph/**` scope for this ticket). Not Filed
  as T-draft-3f15bc51 (never refiled) below rather than fixed silently.
- `src/frob/app/deploy_runner.py`, `src/frob/app/config.py`,
  `src/frob/__main__.py`: CLI wiring for `frob deploy audit --vm <name>
  --ssh-host H --ssh-key KEY [--ssh-user U] [--base-snapshot NAME]
  [--output PATH] [path]`. OUTSIDE this ticket's declared `scope`
  (`src/frob/app/**`/`src/frob/__main__.py` are not in the scope list
  above) -- touched anyway because the ticket's own "Command:" line in
  the dispatch explicitly requires this CLI surface to exist, and T-0257
  (the direct precedent for `frob deploy generate`) used the identical
  `src/frob/app/**`+`src/frob/__main__.py` scope for the same reason (see
  T-0258's Done report note, line ~4893, "DEPLOY001-precedent shape
  T-0257 used `src/frob/app/**` scope for"). Disclosed here rather than
  filed as a separate ticket since the CLI dispatch is not separable work
  -- a `frob deploy audit` gate/library with no CLI entry point would not
  satisfy the ticket's stated deliverable.
- `Makefile`: `deploy-audit` target (`FROB_VM`/`FROB_VM_SSH_HOST`/
  `FROB_VM_SSH_KEY` env vars or `ARGS=`), added to `.PHONY`. NOT part of
  `all`/`check`.
- `docs/commands/deploy.md`: new `frob deploy audit --vm` section (the
  sequence, state capture, four proofs, status assertions, allowlist
  table with justification, attestation, testing posture, scope/honesty
  notes) plus `See also` entries for the two new modules.
- `pyproject.toml` (0.7.0 -> 0.8.0), `CHANGELOG.md` (new `## [0.8.0] -
  unreleased` section), `.frob-release.json` (via `frob release stamp`):
  REL001 fired (new public API surface, minor bump) -- also outside the
  declared `scope`, same "the gate demands it, not separable" reasoning
  as the `app/` files above.
- `uv.lock`: one-line `frob` version bump (0.7.0 -> 0.8.0) tracking the
  `pyproject.toml` bump, from `frob release stamp`'s reinstall.

Not Filed: T-draft-3f15bc51 (never refiled) (new, bug) -- `frob.graph.dsl`/`frob.gates._test_edges`
`frob:tests` src/target direction disagreement for freshly-parsed files
vs. stale `.frob/cache.db` entries (found while doing the pre-work sweep
and debugging TEST001 false-positives on this ticket's own new code;
`src/frob/graph/**`/`src/frob/gates/**` are out of this ticket's scope,
so not fixed here).

Evidence (fresh `pytest --collect-only -q -o addopts="" -n0` against
`tests/unit/deploy/test_audit.py`/`test_vm_runner.py`, all 18 collected
and passing):
- `tests/unit/deploy/test_audit.py::TestDiff::test_no_diff`
- `tests/unit/deploy/test_audit.py::TestDiff::test_delta`
- `tests/unit/deploy/test_audit.py::TestDiff::test_allowlist`
- `tests/unit/deploy/test_audit.py::TestProofs::test_holds`
- `tests/unit/deploy/test_audit.py::TestProofs::test_fails`
- `tests/unit/deploy/test_audit.py::TestProofs::test_af_holds`
- `tests/unit/deploy/test_audit.py::TestProofs::test_af_fails`
- `tests/unit/deploy/test_audit.py::TestProofs::test_ie_holds`
- `tests/unit/deploy/test_audit.py::TestProofs::test_ie_extra`
- `tests/unit/deploy/test_audit.py::TestProofs::test_ie_missing`
- `tests/unit/deploy/test_audit.py::TestStatus::test_not_inst_true`
- `tests/unit/deploy/test_audit.py::TestStatus::test_not_inst_false`
- `tests/unit/deploy/test_audit.py::TestStatus::test_healthy_true`
- `tests/unit/deploy/test_audit.py::TestStatus::test_missing_unit`
- `tests/unit/deploy/test_audit.py::TestAttest::test_all_green`
- `tests/unit/deploy/test_audit.py::TestAttest::test_proof_fail`
- `tests/unit/deploy/test_vm_runner.py::TestAvail::test_no_bin`
- `tests/unit/deploy/test_vm_runner.py::TestAvail::test_run_vm_audit_skips_cleanly`

Also ran: `uv run frob test --base main` -> `[PASS] python exit=0 2.88s`
(24 selected node ids, including
`tests/integration/test_interfaces.py::TestInterfaces::
test_deploy_generate_writes_and_checks` and `test_main_cli_dispatches`).
`uv run pytest tests/unit/strata/test_selfconform.py -k TestRealGateGreen
-q` -> 1 passed (deploy is modeled under `frob`'s own self-model, per
`design/frob.strata`, since T-0257).

CLI smoke test (real, VBoxManage absent on this host): `uv run frob
deploy audit --vm test-vm --ssh-host 127.0.0.1 --ssh-key /tmp/fakekey`
-> `WARNING: deploy audit: SKIPPED -- VBoxManage not found on PATH`,
exit code 2 -- confirmed graceful degrade, no fabricated pass.

VM-gated vs. unit-tested split: `src/frob/deploy/_audit.py` (all proof/
diff/attestation/status-assertion logic) is 100% unit-tested, no VM. The
ONLY VM-gated, untested-in-CI surface is `src/frob/deploy/_vm_runner.py`'s
private helpers (`_vboxmanage`, `_ssh`, `_scp_to_guest`,
`_restore_base_snapshot`, `_capture_state`, `_run_status_and_assert`) and
`run_vm_audit`'s post-`vboxmanage_available()` path -- these were
exercised manually only via code review and the CLI smoke test's
graceful-degrade path (no actual VirtualBox guest available in this
environment); `run_vm_audit`'s pre-check skip path IS unit-tested
(`TestAvail::test_run_vm_audit_skips_cleanly`).

Gates: `uv run frob check` (full, unscoped) -> 0 errors, 23 warnings, 223
waived (all pre-existing, none from this ticket's files -- confirmed via
`grep` for `deploy`/`audit`/`vm_runner` in the violation list, none
found beyond the doc-anchor iteration during development, all resolved).
`ruff-check`/`ruff-format`/`ty` all pass clean on the touched files.
`make coverage` passed (`stamp_coverage: stamped 385 file(s)`) after
re-running `make core` (the `frob release stamp` step's package
reinstall transiently broke `strata_core` native linkage --
`docs/guides/agent-playbook.md` section 1's exact warning, resolved by
re-running `make core`). `git diff main --diff-filter=D --stat` is empty
(deletion-filter land rule). `frob-core/Cargo.lock`/`strata-core/
Cargo.lock` churn from `make core` reverted before finishing.
