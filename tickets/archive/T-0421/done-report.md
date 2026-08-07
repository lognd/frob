## Done report

Added an honest third state to `frob check`'s per-language display
(T-0421): a language present in the project but with no file matching its
own suffixes changed since `check_base` now reports `SKIPPED: <lang>
(unchanged since base)` instead of always silently re-running, when the
new `check_skip_unchanged` opt-in is on (`frob.toml`'s `[check]
skip_unchanged = true` only -- deliberately no CLI flag, to keep
`__main__.py`'s argument surface untouched per the coordinator's
conflict note). `_language_unchanged` (`frob.app.check_runner`) reuses
`frob.gitio.working_diff`'s existing merge-base hunk listing (the same
change surface `--delta` already diffs against) rather than a second
bespoke git invocation, and defaults to "changed" (never silently skip)
on any git failure. A language genuinely absent from the project (no
`Cargo.toml`/`CMakeLists.txt`/etc.) still shows no line at all --
`_detected_types` never names it, unchanged from before. Wired into
`_run_all_detected` (multi-language auto-detect path only; a pinned
`--type` always runs its one stage, matching the ticket's "skipped vs
hidden" framing being about the auto-detect list).

`AppConfig` gained one new field, `check_skip_unchanged: bool = False`
(default off, fully backward compatible).

Verified: 3 new unit tests in `tests/unit/test_app_runners_batch6.py::
TestSkipUnchangedLanguage` (unchanged-shows-SKIPPED, changed-still-runs,
absent-language-never-shown) plus the existing check_runner/config test
suites, all green. Also confirmed by construction that
`_unchanged_skip_result`'s tool name (`skipped:<lang>`) and summary
string are distinct from `_skip_note_result`'s pinned-away case
(`skipped:<lang>` there is `f"skipped:{skipped}"` with a "(pinned to ...)"
summary) so the two SKIPPED reasons never read as the same thing.

Caveat: most of this ticket's actual code (the `_language_unchanged`/
`_unchanged_skip_result` functions and `_run_all_detected`'s wiring) was
implemented and committed together with T-0420's check_runner.py edits
in the "split gates line" commit, before I split my attention back to
finish T-0421 separately -- the commit message on that earlier commit
does not mention T-0421. This commit (amended once, locally, to add a
"(T-0421)" tag to its own subject so `frob check`'s SCOPE001 cross-ticket
exemption resolves cleanly for T-0420) is the remainder: AppConfig's new
field, the frob:tests directive dot-syntax fix, and the new test class.

### Changed
```
 src/frob/app/check_runner.py          | 271 ++++++++++++++++++++++++++++++++--
 src/frob/app/config.py                |   8 +
 src/frob/check/_python.py             | 127 ++++++++++++++--
 tests/system/test_cli_check.py        |   8 +-
 tests/unit/test_app_runners_batch6.py |  89 +++++++++++
 tests/unit/test_check.py              |  23 ++-
 tickets.md                            | 144 +++++++++++++++++-
 7 files changed, 625 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_unchanged_python_reports_skipped_not_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_changed_python_still_runs` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_absent_language_never_shown` (pytest node id, verified passing when recorded)
