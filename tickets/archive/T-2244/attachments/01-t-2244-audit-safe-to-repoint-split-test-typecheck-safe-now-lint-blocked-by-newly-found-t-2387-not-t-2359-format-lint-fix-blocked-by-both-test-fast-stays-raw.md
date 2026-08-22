# T-2244 audit: which Makefile aliases are safe to repoint today, independent of the formatter question

Filed by an agent investigating T-2346/T-2356 (ledger v2 cutover) at the
coordinator's request, per the standing instruction not to attempt the
138-file reformat (T-2359, deliberately held for a quiet fleet). This
records a decided split so whoever gets the quiet window (or picks this
leaf up before then) has real findings instead of a fresh investigation.

## SAFE to repoint TODAY, verified directly against this repo's current
## tree, blocked by nothing

- `test:` -> `uv run frob quality test --all`
  Already verified with matching parity by T-2252 (its own Done report:
  "net pytest invocation is identical to today's `pytest tests/ -q -n
  auto`"). No further work needed for this one line.

- `typecheck:` -> `uv run frob check --only ty`
  Verified directly just now: `frob check --only ty` runs ONLY `ty
  check` (0 errors, `pass ty no issues`), exactly matching today's
  `typecheck:` recipe (`uv run ty check $(SRC)/`) with nothing else
  running. This is a strictly simpler, more direct repoint than the
  `--skip-*` combination the original ticket text sketched, and it does
  not touch ruff-format at all -- unaffected by both the 138-file debt
  and the newly-found bug below.

## LIKELY SAFE, needs one timed parity run before repointing (not done
## here -- each is a multi-minute full-suite run, out of scope for a
## quick audit)

- `test-unit:` -> `uv run frob quality test tests/unit --all`
- `test-integration:` -> `uv run frob quality test tests/integration --all`
- `test-system:` -> `uv run frob quality test tests/system --all`
  T-2319 (done) added real directory-scoped SELECTION via the `path`
  positional ("matches `pytest PATH`'s subset semantics" per its own
  `--help` text) -- this was the exact gap that blocked these three
  lines before. `tests/unit/` collects 4829 items via plain pytest
  (verified). A `frob quality test tests/unit --all` run needs `--all`
  alongside the path (path alone resolves root only per earlier
  measurement) -- confirm collected count and exit-code parity in one
  timed run per target before flipping the Makefile; each is a multi-
  minute run so not done as part of this audit.

## NOT SAFE YET -- and the reason is NOT what it first looks like

- `lint:` (today: `ruff check` + `ty check`, deliberately NO format
  check) is blocked, but NOT primarily by the 138-file reformat --
  it is blocked by a NEWLY DISCOVERED, currently-failing regression:
  **T-2387** (filed just now, kind=bug): T-2320's new split flags
  (`--skip-ruff-check`/`--skip-ruff-format`) and `--fix-ruff` are parsed
  correctly by argparse but silently dropped before `AppConfig(**d)` --
  `_BOOL_FLAGS` (src/frob/app/_config_external.py:337) was never updated
  to include their three new dest names, the EXACT bug class T-0749
  already named and fixed once for `--accepts N`. Reproduced directly:
  `frob check --skip-ruff-format ... --no-cache` still reports `FAIL
  ruff-format 138 files would be reformatted` -- the flag has no effect
  from the CLI. There is ALSO an existing, purpose-built detector for
  this exact class (`find_dropped_cli_flags`, T-2004) with its own test
  (`tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags`)
  -- that test is CURRENTLY RED on main right now, failing with exactly
  `check_ruff_fix`, `check_skip_ruff_check`, `check_skip_ruff_format`.
  Once T-2387 lands, `lint:` -> `uv run frob check --skip-ruff-format
  --skip-arch --skip-cycle --skip-dup --skip-bind --skip-exports
  --skip-gates --skip-tests` becomes a clean repoint matching today's
  scope exactly (ruff-check + ty, no format check) -- WITHOUT needing
  T-2359 at all, since it never asks for a format check in the first
  place.

- `format:`/`lint-fix:` (today: `ruff check --fix` + `ruff format`,
  real write-mode) are blocked by BOTH T-2387 (the same dropped-flag
  bug also silently no-ops `--fix-ruff` -- `check_ruff_fix` never
  reaches `True`, so `frob check --fix-ruff` today runs a normal
  read-only check instead of the "genuine ruff-autofix WRITE pass" it
  claims to, with no error) AND T-2359 (once `--fix-ruff` actually
  works, running it against the CURRENT tree's 138 pending files is
  exactly the repo-wide detonation T-2359 exists to sequence away from
  -- these two conditions are independent, both must clear).

- `test-fast:` stays on raw `pytest --testmon` -- no `frob quality
  test` equivalent exists today (confirmed: no fuzz/testmon-shaped flag
  in `frob quality test --help`). This is a decided, disclosed gap, not
  a blocked item -- nothing to wait on, it simply does not migrate.

## Summary table

| target           | status          | blocked by          |
|------------------|-----------------|----------------------|
| test:            | SAFE, done      | nothing              |
| typecheck:       | SAFE, verified  | nothing              |
| test-unit:       | likely safe     | one timed parity run |
| test-integration:| likely safe     | one timed parity run |
| test-system:     | likely safe     | one timed parity run |
| lint:            | blocked         | T-2387 only          |
| format:          | blocked         | T-2387 AND T-2359    |
| lint-fix:        | blocked         | T-2387 AND T-2359    |
| test-fast:       | stays raw       | nothing (disclosed)  |

Two of nine lines are safe right now; three more need only a timed
verification run, no code changes. T-2387 unblocks a THIRD target
(lint:) independent of the reformat -- the original framing ("blocked
behind T-2359") undercounted what a single small CLI fix (T-2387)
unlocks on its own.
