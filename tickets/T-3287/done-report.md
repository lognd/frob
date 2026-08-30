## Done report

THE ANCHOR: `git rev-parse --git-common-dir`'s PARENT directory
(`frob.gitio.git_common_dir`, already memoized per-process, T-0784) --
resolves to the SAME primary-checkout path from inside any linked
worktree of one repo, since git resolves it itself rather than a naive
parent-directory walk (confirmed against this repo's own unusual layout,
worktrees nested under `.claude/worktrees/` INSIDE the primary
checkout). New `_admission_registry_anchor(root)`: checks `(root /
".git").exists()` first and returns `root` unchanged if absent (skips
`git_common_dir` entirely rather than calling it and discarding its
Err -- `git_common_dir` logs a WARNING on a failed git call, correct for
its OTHER callers where "not a git repo" is unexpected, but here it is
the NORMAL degrade path, and calling it unconditionally broke the
existing must-stay-quiet fixture with log noise, caught and fixed before
landing). `_admission_dir` now builds `<anchor>/.frob/check-admission`
instead of `<root>/.frob/check-admission`.

WHY THIS DOES NOT DOUBLE-COUNT AGAINST MEMORY, WHY NOT MACHINE-GLOBAL:
stated directly in `_admission_registry_anchor`'s own docstring, per the
ticket's 2026-08-28 clarification -- `_available_memory_mb` already
covers cross-REPO machine contention (reads whole-box `/proc/meminfo`
`MemAvailable`), left completely unchanged; the divisor only needed to
start seeing siblings WITHIN one repo's own worktrees, and a git-common-
dir anchor is exactly that grain: shared within one repo, distinct
across different repos, never a `/tmp` path.

STALENESS: unchanged mechanism (`_live_concurrent_checks`'s existing
`_pid_alive`-gated reap-on-read), now exercised end-to-end against the
shared anchor (new fixture: a live worktree-A registration plus a
directly-written stale-pid marker in the SAME shared registry --
reaped, not counted).

MEASUREMENT: unit-level, deterministic (real `git init` + `git worktree
add` fixtures, not mocked git plumbing) rather than a live re-run of the
original field measurement -- the fleet's OTHER currently-running `frob
check` processes are still on unpatched code (pre-T-3287) until this
lands and they rebase, so a live "several series, markers > 1" capture
right now would only prove the OLD per-worktree behavior, not the fix.
Manually confirmed instead that calling `_admission_registry_anchor`
from this worktree (`.claude/worktrees/t-3287`) resolves to
`/home/logan/projects/frob` (the primary checkout), matching the
existing single marker already present at
`/home/logan/projects/frob/.frob/check-admission/`.

MUST-FIRE: TestAdmissionRegistryAnchor::test_two_worktrees_of_one_repo_share_one_anchor,
           TestAdmissionRegistryAnchor::test_two_worktrees_see_each_others_markers
MUST-STAY-QUIET: TestAdmissionRegistryAnchor::test_non_git_root_falls_back_to_itself,
                 TestAdmissionRegistryAnchor::test_two_unrelated_repos_do_not_throttle_each_other,
                 TestAdmissionRegistryAnchor::test_primary_checkout_anchors_to_itself
                 (plus all 25 pre-existing TestAdmissionBudgetContextManager/etc. tests
                 still pass unchanged, including the log-silence fixture)
THIRD FIXTURE: TestAdmissionRegistryAnchor::test_stale_marker_from_dead_pid_does_not_permanently_deflate_shared_budget

`FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist tests/unit/test_check_admission.py -v`:
31 passed (25 pre-existing + 6 new).
`uv run frob test --base main --fallback warn`: python exit=0, 8 test(s).
`frob check --ticket T-3287`: gate:SCOPE 0 errors (75 pre-existing
docs/modules/gates.md anchor-coverage warnings unrelated to this diff).
ty/ruff-format findings in that report belong to files this ticket does
not touch (same pre-existing baseline T-3275 already disclosed).

### Changed
```
 tickets/T-3287/ticket.md | 17 ++++++++++++++++-
 1 file changed, 16 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_worktrees_of_one_repo_share_one_anchor` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_worktrees_see_each_others_markers` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_non_git_root_falls_back_to_itself` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_unrelated_repos_do_not_throttle_each_other` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_stale_marker_from_dead_pid_does_not_permanently_deflate_shared_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_primary_checkout_anchors_to_itself` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 13 error(s), 4043 warning(s), 856 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3287, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py
