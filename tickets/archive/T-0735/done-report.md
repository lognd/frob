## Done report

Epic close verification (T-0735): both declared children (T-0864, T-0865 --
the ticket's own `blocked_by` list) are `state: done`. Searched both
tickets.md and tickets-archive.md for `parent: T-0735` -- only T-0864 and
T-0865 reference it; no other child exists.

Verified the parent's own acceptance against reality rather than trusting
the children's claims:
- Read the repo Makefile directly: the `core:` target
  (Makefile:362-364) is exactly the one-line shim `uv run frob natives
  build`, with the `# frob:managed-block END makefile-core-shim` marker
  immediately after it -- no CARGO_TARGET_DIR assignment or maturin-develop
  invocation left in the Makefile itself (the T-0732 drift this epic exists
  to retire).
- Ran `uv run frob natives build` foreground in this repo: both declared
  [natives] crates (strata_core, frob_core) built cleanly via `maturin
  develop --uv --release`, using `cargo_target_dir=/home/logan/projects/
  frob/.git/frob-cargo-target-cache` -- the git-common-dir-keyed shared
  cache path T-0732/T-0864 designed (`git -C . rev-parse --git-common-dir`
  resolved once, logged in the command's own output), NOT a per-worktree
  path. The build was fast (cache hit from this session's earlier `make
  core` runs), matching "mostly cached" expectations for a repeat build.

Acceptance criterion (`GIVEN any frob-enabled repo with [natives] WHEN uv
run frob natives build runs THEN natives compile with the shared per-clone
cache and the repo Makefile contains no cache logic`) holds for THIS repo,
verified directly, not by proxy.

Estate rollout: T-0735's own user-directive text names "estate rollout via
fleet at close" as part of the epic. That rollout -- walking every OTHER
frob-enabled repo, running `frob scaffold apply` to convert each one's
Makefile core target and applying T-0865's drift check -- is fleet-level
work outside this repo's own tree and cannot be verified or performed from
inside this worktree. Filed T-1031 ("frob natives build: estate
rollout of the Makefile core one-line shim across sibling repos", scope
docs/**) as the honest follow-up rather than either forcing a fleet
operation this repo has no reach into, or silently dropping the directive.
This repo itself is already fully compliant (verified above); the parent
closes on that basis, citing the draft ticket for the estate-wide half.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives` (pytest node id, verified passing when recorded)
- `tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_is_one_line_natives_build_shim` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate::test_applying_to_fresh_repo_installs_one_line_shim` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_unmanaged_core_target_reports_stale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 6536 warning(s), 339 waived
- error-findings: none (measured, zero errors)
