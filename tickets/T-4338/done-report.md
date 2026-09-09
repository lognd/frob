## Done report

Changed:
- .github/workflows/ci.yml (env.UV_VERSION/RUST_TOOLCHAIN_VERSION/MATURIN_VERSION pins; version/toolchain/maturin-version with: fields on every astral-sh/setup-uv, dtolnay/rust-toolchain, PyO3/maturin-action step; "Print resolved toolchain versions" step added to build and standalone-install jobs; pin-advancement-ownership doctrine comment)
- tests/test_ci_workflow_toolchain_pins.py (new: TestUvVersionIsPinned, TestRustToolchainVersionIsPinned, TestMaturinVersionIsPinned, TestResolvedToolchainVersionsAreReported, _assert_every_step_pins, _load_ci_workflow)
- design/frob.strata (testsuite node's fs.read via-list: added tests/test_ci_workflow_toolchain_pins.py)
- docs/design/registry/capability-via-ratchet.lock.json (testsuite::fs.read accepted_count 224 -> 225, reason cites T-4338)

Evidence:
- pytest tests/test_ci_workflow_toolchain_pins.py tests/test_ci_workflow_actions_pinned.py tests/test_ci_workflow_matrix.py -- 29/29 passed
- frob test --base main --fallback warn -- 38 python test outcomes recorded, exit 0, PASS
- frob check --ticket T-4338 -- 1 error (gate:DRIFT DRIFT002, docs/guides/agent-playbook-appendix.md, owned by T-4345, pre-existing and unrelated to this diff); 0 errors in every gate this ticket's scope can affect (SCOPE, PRE, COV, WIRE, DUP, SELFAUDIT, SYS111 ratchet all clean after fixes)

Survey (toolchain inputs this workflow installs, per the ticket's ask):
Three, all now pinned. Before this change, none were: `uv` (astral-sh/setup-uv, no `version:`), the Rust toolchain (dtolnay/rust-toolchain, no `toolchain:`, defaulted to whatever "stable" resolved to that day), and `maturin` (PyO3/maturin-action, no `maturin-version:`, installed latest-matching-constraint at run time). All three are now workflow-level `env` pins (UV_VERSION, RUST_TOOLCHAIN_VERSION, MATURIN_VERSION) read by every step in both jobs (`build` and `standalone-install`) that installs that tool.

State-what-it-used:
Both jobs now carry a "Print resolved toolchain versions (T-4338)" step that writes `uv --version`/`rustc --version`/`cargo --version` (and the pinned maturin version, deterministic by the pin itself) to $GITHUB_STEP_SUMMARY, unconditionally (not `if: failure()`), so a reader of any run -- passing or failing -- sees what it used without inferring it from setup-action cache-hit/miss log lines.

Pin-advancement ownership (decided and recorded in ci.yml itself):
These three pins are deliberately OUTSIDE `.github/dependabot.yml`'s scope. Dependabot's github-actions ecosystem (T-3922) tracks `uses: ...@sha` references; it has no mechanism that watches a `with:` input's string value, so it would never touch UV_VERSION/RUST_TOOLCHAIN_VERSION/MATURIN_VERSION. Advancing them is recorded as a manual decision: bump the env value, rerun the workflow, confirm the resolved-versions step summary on all three legs, then land. T-4268's dependabot-sequencing plan only ever governs the `uses:` SHAs and does not apply to these.

VERIFICATION GAP (stated plainly, per the ticket's own instruction):
I could not trigger a real GitHub Actions run against this change -- doing so requires pushing this ticket's commit to origin (this session works in a local worktree/branch; `frob ticket land` publishes to local main only), which is outside a ticket-close's normal scope and was not separately requested. So the ticket's own verification bar -- "confirming the resolved tool version is identical across all three platform legs of one run, and quoting the three values" -- is UNVERIFIED by me. What IS verified: the config parses, the pins are structurally present and read from one place on every relevant step (tests/test_ci_workflow_toolchain_pins.py), and `frob check`/`frob test` are clean. What remains unverified: the actual resolved uv/rustc/cargo values GitHub Actions' three runners produce for ubuntu-latest/windows-latest/macos-latest on a real push. Identical pins in ci.yml are NOT that evidence -- only a real run's three resolved values are, and I have none to quote. This should be confirmed by whoever next pushes/lands this change and can read the Actions run's step summaries.

Filed: none

Gates: frob check --ticket T-4338 clean (1 pre-existing DRIFT002 error owned by T-4345, unrelated to this diff)

### Changed
```
 tickets/T-4338/done-report.md | 42 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4338/ticket.md      | 32 +++++++++++++++++++++++++++++++-
 2 files changed, 73 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_toolchain_pins.py::TestUvVersionIsPinned::test_workflow_declares_a_uv_version_pin` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestUvVersionIsPinned::test_every_setup_uv_step_pins_the_shared_version` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestRustToolchainVersionIsPinned::test_workflow_declares_a_rust_toolchain_pin` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestRustToolchainVersionIsPinned::test_every_rust_toolchain_step_pins_the_shared_version` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestMaturinVersionIsPinned::test_workflow_declares_a_maturin_version_pin` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestMaturinVersionIsPinned::test_every_maturin_action_step_pins_the_shared_version` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestResolvedToolchainVersionsAreReported::test_build_job_prints_resolved_toolchain_versions` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_toolchain_pins.py::TestResolvedToolchainVersionsAreReported::test_standalone_install_job_prints_resolved_toolchain_versions` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_actions_pinned.py::TestGitHubActionsArePinnedToShas::test_ci_workflow_yaml_still_parses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 1 error(s), 4719 warning(s), 955 waived
- error-findings: DRIFT002@docs/guides/agent-playbook-appendix.md
