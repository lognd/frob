## Done report

Reproduced first: confirmed on current main (tip 454a439, no later fix
existed) via a temp non-frob repo (`/tmp/nonfrobrepo2`, a minimal
`design/foo.strata` + `src/foo/main.py`) run through
`frob sys audit .` -- printed
`WARNING: selfconform: /tmp/nonfrobrepo2/src/frob does not exist` even
though `sys audit: self-conformance PROVED -- zero SYS gaps` also printed,
exactly the "vacuous-looking proof" the ticket describes. Not a T-0308-style
already-fixed case; the code change below was needed.

Assumption location: `src/frob/strata/_selfconform.py::_top_level_dirs`
(the SYS102 "unmodeled code" helper). `_PACKAGE_ROOT = "src/frob"` (module
constant, line ~102) is frob's own package layout, declared correct for
`design/frob.strata`'s self-audit (module docstring). `_top_level_dirs`
unconditionally logged `_log.warning("selfconform: %s does not exist", ...)`
whenever `root / _PACKAGE_ROOT` was not a directory -- true for literally
every non-frob repo running `frob sys audit`, since `check_self_conformance`
is invoked generically by `frob.app.sys_runner` on any repo root, not just
frob's own.

Fix: changed the log call from `_log.warning` to `_log.debug` (kept, not
silenced outright, so frob's own SYS102 detection is still traceable) and
expanded the message to state plainly that this means "not the frob repo
(or repo root mismatch); skipping SYS102". Behavior (empty `SYS102`
finding set) was already correct on the missing-directory path -- only the
log severity/wording changed. No general repo-discovery code was touched;
the fix is scoped entirely to the one frob-specific helper that already
owned this frob-specific constant.

Verify: re-ran the same repro after the fix -- `frob sys audit .` in
`/tmp/nonfrobrepo2` now logs
`selfconform: /tmp/nonfrobrepo2/src/frob does not exist -- not the frob repo
(or repo root mismatch); skipping SYS102 unmodeled-code check` with NO
`WARNING:` prefix (`FrobFormatter` only prefixes WARNING+; DEBUG/INFO print
bare), and `sys audit: self-conformance PROVED` unchanged. Ran `frob sys
audit .` inside this worktree (frob's own repo, `src/frob/` present) --
selfconform log block shows zero `does not exist` line at all, i.e. frob's
own SYS102 behavior is byte-for-byte unchanged (still 0 violations, 0
waived, 0 stale).

Litmus test added:
`tests/unit/strata/test_selfconform.py::TestUnmodeledCodeMissingPackageRoot::test_missing_package_root_produces_no_warning`
-- builds a `tmp_path` repo with no `src/frob/` at all, asserts
`check_self_conformance` returns zero `SYS_UNMODELED_CODE` violations AND
zero log records at WARNING level or above containing "selfconform" (using
`caplog.at_level("DEBUG", logger="frob")`).

Changed:
- src/frob/strata/_selfconform.py :: _top_level_dirs -- log level
  warning -> debug + clarified message when `src/frob/` is absent
- tests/unit/strata/test_selfconform.py :: TestUnmodeledCodeMissingPackageRoot -- new litmus test class

Evidence (all node ids observed in a fresh `pytest --collect-only -n0` pass
from a `make core`-built worktree):
- tests/unit/strata/test_selfconform.py::TestUnmodeledCodeMissingPackageRoot::test_missing_package_root_produces_no_warning
- `uv run pytest tests/unit/strata/test_selfconform.py -q -n auto` -> 35 passed
- `uv run pytest tests/unit/strata -q -n auto` -> 383 passed (full strata unit suite, no regressions)
- `uv run ruff check src/frob/strata/_selfconform.py tests/unit/strata/test_selfconform.py` -> All checks passed (both PATH `ruff` and `uv run ruff`)
- `uv run ruff format --check` -> clean after one `ruff format` pass on the new test file (pre-existing formatting difference in a test-only file, applied and re-verified)
- `uv run ty check src/frob/strata/_selfconform.py` -> All checks passed
- `uv run frob check` (post `make core`, post-change) -> `gates 0 errors, 1 warning, 24 waived` (the 1 warning and all 24 waivers are pre-existing/unrelated -- no new violation introduced)
- `git diff main --diff-filter=D --stat` -> empty (deletion-filter land rule clean)

Filed: none -- no out-of-scope issue found during this fix.

Gates: `frob check --ticket T-0211` implicitly covered by the full `frob
check` run above (0 errors); no waiver needed for this change.

Not closing -- leaving for reviewer per the review-gated workflow.
