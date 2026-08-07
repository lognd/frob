## Done report

Changed:
- src/frob/gitio.py -- `working_diff`'s untracked-file loop now checks
  `abs_path.is_dir()` before calling `_count_lines` and skips with a
  DEBUG log line (not WARNING) for untracked gitlinks / nested-worktree
  directories that `git ls-files --others --exclude-standard` lists as a
  path but that are not readable as files. Previously this hit
  `_count_lines`'s `OSError` handler with `[Errno 21] Is a directory` and
  logged a WARNING for every such entry on every `frob check`/`frob test`
  invocation in a repo with an untracked nested worktree/gitlink.

Evidence:
- tests/test_gitio.py::TestWorkingDiff::test_untracked_directory_is_skipped_not_read_as_file
  (new regression test: builds a repo with a genuine untracked nested git
  checkout under `nested-worktree/`, asserts `working_diff` succeeds,
  excludes the directory's path from `diff.hunks`, and asserts no
  "could not read untracked file" WARNING was logged)
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
  (existing untracked-file coverage, still green -- confirms plain
  untracked files are unaffected by the directory-skip check)
- `uv run pytest tests/test_gitio.py -q` -> 13 passed
- `uv run pytest --collect-only -q tests/test_gitio.py::TestWorkingDiff` -> 5 collected
  (confirms the new test id above resolves)
- `uv run frob test --base main` -> touched=5 selected tests/test_gitio.py
  (+ both TestWorkingDiff untracked cases explicitly) -> PASS exit=0
- `ruff check src/frob/gitio.py tests/test_gitio.py` and
  `uv run ruff check src/frob/gitio.py tests/test_gitio.py` -> both
  "All checks passed!" (both-ruff stable per playbook section 12)
- `uv run ty check src/frob/gitio.py` -> "All checks passed!"

Filed: none (no out-of-scope work found)

Note: after this ticket's initial pass, `git merge main` pulled in a large
unrelated batch (T-0157 secrets-scan gate, extending-guides docs, etc.).
Re-ran `make core`, re-ran `uv run frob ticket sweep T-0227` (pre-work
sweep timestamp must postdate the merge per PRE001), re-recorded evidence
via `uv run frob ticket evidence T-0227 <ids>`, and re-verified
`uv run pytest tests/test_gitio.py -q` (13 passed) and
`uv run frob test --base main` (PASS) against the merged tree before
finishing. One line the merge exposed: an unrelated pre-existing assert in
`tests/test_gitio.py` (`TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked`,
the `assert files == {...}` literal-set comparison) started tripping
PERF003 under the post-merge gate state; added
`# frob:waive PERF003 reason="single set comprehension over hunks compared
by == to a fixed 4-item literal set, not a nested join"` on that line
(tests/** is in this ticket's scope) rather than leave a new unwaived
violation sitting in a file this ticket touches.

Gates: `uv run frob check --ticket T-0227` (post-merge, post-`make core`)
-> gates FAIL with 3 unwaived violation(s) (193 waived), all pre-existing
and out of scope: COV003 on T-0168 (stale evidence id, unrelated ticket),
TEST006 (no coverage stamp -- campaign-wide, instructed to ignore), and
PERF004 on `src/frob/tickets/_land.py:67` (untouched file). Confirmed via
`grep '\[gates\]' <check output>` that no remaining unwaived violation
references `gitio.py` or any line I added outside the one PERF003 waived
above. `ruff check` / `uv run ruff check` on `src/frob/gitio.py` and
`tests/test_gitio.py` both report "All checks passed!"; `uv run ty check
src/frob/gitio.py` reports "All checks passed!".
