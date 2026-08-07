## Done report

frob.lang's `_parse` (tree-sitter) and `_parse_strata_file` (strata-core)
had no upper bound on file size and no wall-clock budget around the actual
parse call, despite visiting files from a potentially untrusted
adopter-repo tree -- a DoS trust-boundary gap (found while working
T-0786).

Fix: `_check_size_cap` rejects any file over `_MAX_PARSE_FILE_BYTES`
(8 MiB) via a `Path.stat().st_size` check BEFORE `read_bytes()` is ever
called, so an oversized file is never even fully read into memory.
`_run_parse_with_timeout` wraps the actual tree-sitter/strata-core parse
call on a single-use daemon-pool thread with a `_PARSE_TIMEOUT_SECONDS`
(10.0s) budget -- neither library exposes a cancellation hook, so a
runaway parse's worker thread is abandoned rather than killed, but the
CALLER is never blocked past the budget. Both guards log a WARNING naming
the file and the exact limit hit (never a silent skip -- the T-0897
silent-drop anti-pattern this explicitly avoids), and both new
`LangError` variants (`FileTooLarge`, `ParseTimedOut`) flow through the
same `frob.graph._process_source_file` -> `ParseFailure` ->
`frob.gates._parse_failures.parse_failure_gate` (PARSE001) path every
other `LangError` already does, so a skip surfaces as an ERROR-tier
`frob check` finding too, not just a log line.

`_parse` itself was refactored to pull the stat+size-check+read sequence
into a new `_read_source_under_cap` helper (shared with
`_parse_strata_file`, removing a near-duplicate) purely to stay under
ARCH001's 60-line function threshold once the new guard logic was added.

docs/modules/lang.md gained a new "Size cap and parse timeout (T-0893)"
section describing both guards and their downstream PARSE001 path.

Scope was extended (via `frob ticket scope T-0893 --add`) beyond the
ticket's original `src/frob/lang/__init__.py`-only scope to include
`tests/test_lang.py` (the regression tests) and `docs/modules/lang.md`
(the new doc section) -- both are direct, necessary companions to the fix
itself, not separate work.

Verification run in this worktree:
- `uv run pytest tests/test_lang.py -p no:cacheprovider -q` -- 48 passed
  (46 pre-existing + 2 new: TestSizeCapAndTimeout::
  test_oversized_file_is_skipped_loudly,
  TestSizeCapAndTimeout::test_parse_timeout_returns_err_not_hang).
- `uv run frob check --ticket T-0893 --only gates-native` -- clean
  (ARCH001 on `_parse` was the one real finding mid-implementation, fixed
  by the `_read_source_under_cap` extraction).
- `uv run frob check --ticket T-0893 --only coverage --only scope
  --only prework --only test --only lang_conformance
  --only lang_project_conformance --only fmt` -- all clean.
- `uv run ruff check` and `uv run ty check` on the touched files -- clean.
- `uv run frob check --ticket T-0893 --only gates-security` showed 2
  pre-existing PII010 errors in `src/frob/deploy/_audit.py`, confirmed
  present on unmodified `main` too (unrelated to this ticket, not fixed
  here).

### Changed
```
 docs/modules/lang.md      |  37 +++++++++++
 src/frob/lang/__init__.py | 164 ++++++++++++++++++++++++++++++++++++++++++----
 tests/test_lang.py        |  60 +++++++++++++++++
 tickets.md                |   3 +-
 4 files changed, 250 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestSizeCapAndTimeout::test_oversized_file_is_skipped_loudly` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestSizeCapAndTimeout::test_parse_timeout_returns_err_not_hang` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
