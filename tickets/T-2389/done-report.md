## Done report

Retargeted the two hardcoded src/frob/ literals T-2384's body named, plus
one sibling found while building T-2388 (folded in per coordinator
instruction, 2026-08-18).

New shared public resolver (frob.lang._nodes, exported via frob.lang):
declared_project_package_name(root) -> str | None (pyproject.toml
[project].name, UNRESOLVED-not-clean-pass on failure per T-2391) and
declared_source_prefixes(root) -> tuple[str, ...] (this project's own
declared source roots, T-2195's _declared_python_source_roots, combined
with the resolved package name into repo-relative "src/<pkg>/"-shaped
prefixes). One shared home, not a third private copy -- per NO
DUPLICATION and T-2384 acceptance[3].

_env_var_docs.py: rel.startswith("src/frob/") -> rel.startswith(source_
prefixes); hardcoded FROB_ env-var prefix -> derived from the resolved
package name uppercased. UNRESOLVED (not a clean pass) if pyproject.toml
can't be read.

_root_asset_dirs.py: _referenced_in_src's rel.startswith("src/frob/") ->
source_prefixes, same UNRESOLVED posture. The non-git-root silent-()
degrade (T-0705's own git-less-target contract) takes priority over
UNRESOLVED -- checked BEFORE package-name resolution, matching every
other gate in this package's existing convention for that case.

_walk_lint.py::tracked_python_files_for_gate: "src/frob" git-ls-files
pathspec literal, shared by WALK001/RENDER001/PORT001(T-2388) alike, is
now an explicit OPTIONAL `pathspec` keyword defaulting to the historical
literal -- WALK001/RENDER001 are unaffected (both genuinely, permanently
about scanning this repo's OWN src/frob/** source, not a portability
bug); a new/retargeted caller passes its own resolved pathspec. T-2388's
own _port_selfcheck.py is disclosed as NOT yet switched over (out of
this ticket's scope, a natural next step).

VERIFICATION (both required per T-2384):
- must-now-fire: two new fixtures, a lograder-named project's own
  LOGRADER_UNDOCUMENTED env var (ENV001) and its own unreferenced
  orphan/ directory (ROOT001) -- both previously invisible off-repo,
  both caught now. Designated repro:
  tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires_for_a_differently_named_project
  confirmed FAILED_AT_PARENT against c0b305c9b (test-only commit, source
  unfixed) -- a genuine repro, not confirmatory-only.
- must-still-pass: this repo's own ENV001/ROOT001/WALK001/RENDER001
  counts, before and after, all unchanged (0/0, 0/0, 30/30, 4/4).
- must-not-false-fire (the epic's SECOND failure direction, ROOT001
  check (a)): a lograder-named project's own legitimately-referenced
  directory (src/lograder/... containing the reference) is correctly
  silent, not flagged -- proving the retarget fixed the false-positive
  direction too, not just silent-pass.

Every existing test fixture needed its own pyproject.toml (both
[project].name AND a src-layout [tool.setuptools] block matching this
repo's own real config) -- without the setuptools declaration,
_declared_python_source_roots has no way to know a fixture uses
src/<pkg>/ layout and falls back to bare-root-relative prefixes only,
silently missing every src/<pkg>/... fixture path. Two existing tests
needed reordering fixes for this (the missing-pyproject UNRESOLVED check
must come AFTER the tracked-files-empty/non-git-root check, not before,
to preserve the pre-existing git-less-target-is-silent contract other
gates in this package already establish).

Two new UNRESOLVED-not-a-clean-pass tests per gate (T-2391 doctrine).

### Changed
```
 src/frob/gates/_env_var_docs.py    | 100 +++++++++++++++------
 src/frob/gates/_root_asset_dirs.py |  61 +++++++++++--
 src/frob/gates/_walk_lint.py       |  23 ++++-
 src/frob/lang/__init__.py          |   4 +
 src/frob/lang/_nodes.py            |  66 ++++++++++++++
 tests/test_gates.py                | 174 ++++++++++++++++++++++++++++++++-----
 tickets/T-2389/ticket.md           |  53 ++++++++++-
 7 files changed, 422 insertions(+), 59 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires_for_a_differently_named_project` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_under_src_frob_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_in_pyproject_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_directory_with_external_reader_declaration_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_makefile_referenced_directory_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_allowlisted_directories_are_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_src_and_tests_dirs_are_never_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_non_git_root_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRootAssetDirGate::test_missing_pyproject_is_unresolved_not_a_clean_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires_for_a_differently_named_project` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_documented_by_literal_string_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_documented_by_constant_name_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_file_scoped_waiver_covers_it` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_non_frob_env_prefixed_constants_are_ignored` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_no_env_assignments_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_non_git_root_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestEnvVarDocGate::test_missing_pyproject_is_unresolved_not_a_clean_pass` (pytest node id, verified passing when recorded)
- `tests/test_walk_lint_gate.py::TestRglob::test_raw_rglob_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_env_var_docs.py, AFFECT001@src/frob/gates/_root_asset_dirs.py, ARCH001@src/frob/gates/_root_asset_dirs.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/retarget-env-root/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/retarget-env-root/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/retarget-env-root/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2389, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/lang/_nodes.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
