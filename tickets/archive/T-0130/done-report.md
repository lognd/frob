## Done report

Changed:
- frob.toml -- added "design/litmus/**" to `[graph].exclude`, mirroring the
  existing `tests/fixtures/**` entry (same list, same load path:
  `frob.excludes.load_exclude_globs`/`is_excluded`, shared by
  frob.graph/frob.dup/frob.arch/frob.app.cycle_runner per T-0026).
- tests/test_excludes.py -- added
  `test_repo_excludes_litmus_strata_from_obligation_surface`, a regression
  test asserting the real repo's frob.toml excludes `design/litmus/*.strata`
  via `load_exclude_globs`/`is_excluded` (the same generic mechanism
  `test_load_and_match_globs`/`test_dup_scanner_honors_exclude` already
  cover with a synthetic tmp_path config).

Mechanism chosen: the shared `[graph]` exclude leaf (frob.excludes), not a
new "graph-tracked but obligation-free" concept -- that distinction does
not exist in frob.graph today (a file is either walked into the graph, with
full COV/TEST obligations, or it isn't). The honest fallback per the
coordinator's instructions was taken: design/litmus is now excluded from
graph build entirely, same as tests/fixtures/**. Tradeoff: design/litmus/*.strata
symbols no longer appear via `frob map`/`frob graph build`'s repo-wide walk,
and `frob xref --lang strata` with a directory root that includes
design/litmus would also skip it if xref grows an exclude check later (it
does not consult [graph] exclude today). Explicit single-file/single-dir
invocations are unaffected because none of `outline_file` (single path,
no directory walk), `xref()` (root can be a file; `_collect_source_files`
has no exclude check), or `frob cycle design/litmus` (exclude globs are
matched against paths relative to `scan_root`, which is `design/litmus`
itself when passed explicitly, so `"design/litmus/**"` never matches) go
through the exclude filter that now hides it from full-repo scans -- see
docs/modules/lang.md and this report's Evidence for how each was
independently re-verified below.

Evidence: tests/test_excludes.py::test_repo_excludes_litmus_strata_from_obligation_surface,
tests/test_excludes.py::test_load_and_match_globs,
tests/test_excludes.py::test_dup_scanner_honors_exclude.
Also manually re-verified (not pytest-bound, CLI smoke checks): `rm -rf .frob
&& frob check --json --only gates` -> 96 diagnostics, exit 0, zero COV001/TEST001
on any `design/litmus` path (Counter: PERF001/2/3/4, TEST002/3 only, all
pre-existing); `frob outline design/litmus/chirp.strata`,
`frob xref Node design/litmus/chirp.strata`, and `frob cycle design/litmus`
all still show real symbols/results; `frob graph build` no longer touches
`design/litmus/*.strata` (grep for the path in its stdout is empty) while
still touching unrelated `tests/unit/strata/test_litmus_*.py` (a distinct,
non-excluded path).

Filed: none -- no further out-of-scope discoveries.
Gates: `frob check` (unscoped, all tools) exits 0, 82 violations all
pre-existing (14 waived, rest warn/info-severity carryover from before
T-0129/T-0130). `frob check --ticket T-0130` reports only SCOPE001 on the
T-0129 files still uncommitted in this same worktree (expected -- those are
T-0129's scope, not T-0130's) plus tickets.md's own SCOPE001 (expected for
any ticket that edits the ledger); no waiver needed for either since they
are cross-ticket, not defects in T-0130 itself.
