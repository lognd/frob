## Done report

Changed:
src/frob/gates/_waive.py::_posix_path
src/frob/gates/_waive.py::_match_waiver

`_match_waiver`'s file-scoped/package-prefix branch compared `violation.file` (always POSIX-relative) against `waiver.src`/`waiver_file` as raw strings; a waiver's `src` built from an OS-native path is `\\`-separated on Windows, so the comparison silently missed there even though the identical waiver matches on Linux/macOS -- surfacing findings like LARGE001 as unwaived errors only on Windows. Added `_posix_path` (backslash -> forward-slash normalization) and applied it to both sides of every comparison in `_match_waiver`'s file-scoped path.

Evidence: tests/gates_suite/test_waive.py::TestMatchWaiverPathShape::test_backslash_waiver_path_still_matches_posix_violation and ::test_backslash_waiver_still_matches_package_prefix -- both construct an Edge with a `PureWindowsPath`-shaped backslash `src` on Linux and assert `_match_waiver` still returns it. Full tests/gates_suite/test_waive.py suite (33 tests) passes.

Filed: none (this IS the filed CI-followup ticket).

Gates: ruff-check/ruff-format/ty clean on the touched files (`uv run ruff check`/`format --diff` both clean; repo-wide gate:ARCH/DRIFT/LARGE errors seen under `frob check --ticket` are pre-existing findings on OTHER files, unrelated to this ticket's touched set). `frob ticket done-report` hung past 590s in this worktree (same pre-existing tool stall seen on T-4391, not investigated further under this ticket's scope) so this section was written directly. `--check-repro` could not produce an automated fail-then-pass verdict for the same T-2025 squash-commit reason as T-4391; manually confirmed both new tests fail (no match returned) against the pre-fix `_match_waiver` and pass against the fixed version.
