## Done report

Changed:
.claude/hooks/_root_write_guard_lib.py::_shell_tokens
tests/test_hook_root_write_guard.py::_env
tests/test_hook_root_write_guard.py (all `env=` call sites switched to `_env()`)
tests/test_hook_root_cleanliness_detector.py::_env
tests/test_hook_root_cleanliness_detector.py (all `env=` call sites switched to `_env()`)
tests/test_hook_frob_suggest.py::_run_hook
tests/test_hook_frob_suggest.py::_run_edit_hook

Root causes (three independent bugs, one shared file each):

1. test_hook_root_write_guard.py / test_hook_root_cleanliness_detector.py:
   their fixtures called `subprocess.run(..., env={...})` (or `env={}`)
   with NO `PATH`. On Linux, CPython's subprocess falls back to
   `os.defpath` when `PATH` is absent from an explicit env (POSIX
   execvpe semantics), so `git` still resolved and the fixtures passed
   by accident. On Windows, `CreateProcess` does no such fallback, so
   `git.exe` was never found; `_worktree_paths` returned `[]`,
   `_root_write_worktree_paths` failed OPEN, and the hook silently
   allowed every write/report the tests expected it to deny/report.
   Fix: a `_env(**extra)` helper in each file that always carries the
   real `PATH` (and `SystemRoot`) plus whatever marker vars a test needs.

2. test_hook_root_write_guard.py's two `~`-expansion tests set only
   `HOME`, but `ntpath.expanduser` (Windows) prefers `USERPROFILE` over
   `HOME`, so the real `USERPROFILE` stayed in force and `~` resolved
   to the wrong directory. Fix: set `USERPROFILE` alongside `HOME`.

3. .claude/hooks/_root_write_guard_lib.py::_shell_tokens used
   `shlex.shlex(..., posix=True, ...)` with its default
   `escape='\\'`, which silently strips every unquoted backslash from a
   token. On Windows, `cd`/`pushd`/redirect targets are native paths
   like `C:\Users\...\agent-wt`, so tokenizing them destroyed the path
   entirely (`C:UsersloganAgentwt`), corrupting effective-cwd and
   redirect-target resolution for every real Windows command this hook
   parses. Fix: `lexer.escape = ""` when `sys.platform == "win32"`
   (POSIX backslash-escape semantics untouched elsewhere).

   Same root cause additionally fixed 4 tests not on the original
   failure list (they were previously masked by bug #1's fail-open:
   test_bash_redirect_inside_worktree_is_allowed_with_no_markers,
   test_bash_set_prefixed_cd_into_worktree_is_allowed,
   test_bash_pushd_into_worktree_is_allowed,
   test_bash_heredoc_body_containing_delimiter_substring_is_allowed).

test_hook_frob_suggest.py's 5 originally-listed failures were state
leakage between tests: `Path.home()` (the hook's O_EXCL marker-state
dir) prefers `USERPROFILE` over `HOME` on Windows too, so the
per-test `home=` isolation silently no-op'd and marker state
accumulated across tests in the REAL home dir. Fix: set `USERPROFILE`
alongside `HOME` in both `_run_hook`/`_run_edit_hook`.

Evidence: 27 originally win32-failing node-ids across all 3 files,
winrun-confirmed passing (bound via `frob ticket evidence`); full
102/102 collected in these 3 files pass on both Windows (winrun) and
Linux (`uv run python -m pytest`).

Filed: T-3780 (draft, empty scope declared -- machine-local tooling outside the repo, not a repo file) -- winsync excludes `.claude/` from the
WSL->Windows mirror sync entirely (both the full `--exclude '.claude/'`
rsync and the incremental `SCAN=(src tests design invariants ...)`
list omit it), so no hook-file edit under `.claude/hooks/` can ever be
verified via `winrun` without a manual out-of-band copy to the mirror.
This blocks ANY hook-file fix in this campaign from being winrun-
verified through the documented workflow; every other hook-cluster
ticket in this drive will hit the identical wall.

Gates: `frob check --ticket T-3777` clean (0 errors, 922 waived,
warnings pre-existing/repo-wide per gate:scope-note). Fixed along the
way: SCOPE001 (extended scope to the two non-src touched files),
COV002 (frob:ticket directive on `_shell_tokens`), SEC110 (waived on
the two `_env()` helpers' PATH/SystemRoot reads -- non-secret), 
SELFAUDIT001/SYS100 (design/frob.strata testsuite env.read via-list) 
and SYS111 (capability-via-ratchet.lock.json ceiling bump 22->24), 
PRE001 (frob ticket sweep re-run after each scope change).

### Changed
```
 .claude/hooks/_root_write_guard_lib.py       |  12 +++
 tests/test_hook_frob_suggest.py              |  19 +++--
 tests/test_hook_root_cleanliness_detector.py |  41 +++++++---
 tests/test_hook_root_write_guard.py          | 116 ++++++++++++++++-----------
 tickets/T-3777/ticket.md                     |  52 +++++++++++-
 tickets/T-3780/ticket.md           |  27 +++++++
 6 files changed, 203 insertions(+), 64 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_refactor_residue_prose_fix_never_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_second_file_rewriting_same_module_import_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_single_file_repeated_edits_never_fire` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_worktree_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_unacked_first_attempt_is_still_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_dirty_root_in_agent_context_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_dirty_root_reported_even_when_cwd_is_the_worktree` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_appending_redirect_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_heredoc_appending_into_checkout_still_refused_with_delimiter_substring` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_heredoc_redirected_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_redirect_into_primary_with_no_marker_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_redirect_target_inside_primary_via_home_relative_path_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_relative_redirect_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_set_prefixed_cd_into_primary_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_tee_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_land_still_refused_alongside_quoted_prose` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_truncating_redirect_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_variable_redirect_target_into_checkout_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_land_with_no_worktree_flag_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_land_with_unregistered_worktree_path_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_no_marker_write_to_root_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_with_no_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_refusal_names_the_recovery_recipe` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_stale_agent_env_vars_do_not_exempt_a_root_write` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 27 passed (from 27 evidence id(s))
- gates: 0 error(s), 4339 warning(s), 922 waived
- error-findings: none (measured, zero errors)
