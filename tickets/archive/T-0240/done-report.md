## Done report

Changed:
- src/frob/gates/_prework.py::_scope_pattern_scan_path (new)
- src/frob/gates/_prework.py::_is_scan_path_pruned (new)
- src/frob/gates/_prework.py::_real_symbol_for_scope_pattern (new)
- src/frob/gates/_prework.py::sweep_ticket (fixed)

Root cause: `sweep_ticket`'s xref loop already computed a per-pattern
`scan_path` (the glob's literal prefix directory) but then called
`xref(symbol, root)` -- the FULL repo root, not `scan_path` -- so every
scope pattern re-walked the entire tree (`xref`'s own `_collect_source_files`
uses `root.rglob("*")` with no exclude-glob or skip-dir awareness, only a
dot-prefix/`__pycache__` filter; `src/frob/xref/**` is out of T-0240's
declared scope so that walker itself was not touched). The search term was
also `Path(pattern).stem`, a glob-syntax guess (`"**"` for any `**`-suffixed
pattern, `"__init__"`/`"README"` for path-shaped patterns) that is almost
never a real symbol, so most xref calls did a full walk and found nothing
useful.

Fix: `xref` is now called with the already-computed `scan_path` (bounding
the walk to that subtree) instead of `root`; `_is_scan_path_pruned` skips
any scan path that is itself a `frob.excludes.is_skipped_dir` name or
matches `[graph] exclude` via `frob.excludes.is_excluded` (both read
through `load_exclude_globs` -- no second copy of the exclude rule, per
the ticket's instruction to reuse `frob.excludes`, the same module
T-0239/T-0274 consult); and `_real_symbol_for_scope_pattern` derives the
xref term from the already-built obligation graph's public symbols under
that subtree (via `frob.tickets.scope_matches`) instead of a stem guess, so
xref only ever searches for names that actually exist. The graph is now
built/loaded ONCE per sweep and reused for both the xref lookup and
`scope_digest` (previously built again after the xref loop).

Measured effect (this repo, Linux fs, `uv run frob ticket sweep T-0240`):
a single `xref(symbol, root)` call against this repo's own root took 1.71s;
the same symbol scoped to `xref(symbol, scan_path)` for a single package
subdir took 0.096s -- roughly 18x per xref call, and the sweep issues one
such call per scope-glob entry, so a multi-glob scope on a slow mount
(the malmberg pilot's `/mnt/c` case) compounds this per pattern. The
`dup_findings` half (`find_duplicates`) was already excludes-aware
(T-0026) and untouched.

Not done in this ticket (filed separately, both out of T-0240's declared
scope which was tickets/gates/dup/tests/tickets.md only):
- `app/ticket_runner.py`'s `_run_sweep`/`_xref_hits_for_scope` carry an
  identical copy of the same two bugs (T-0236 already flagged this call-site
  duplication as follow-up debt) -- not filed as T-draft-3efcb40e (never refiled).
- The SIGINT-message, PRE001 catch-22-on-slow-mounts, and scope_digest
  content-keying items the ticket said to "also fold in" are separate
  design questions, not bugfixes, and were not attempted here -- filed as
  T-draft-ae3416b9 (never refiled).

Evidence:
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_honors_graph_excludes
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_skips_builtin_skip_dirs
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_xref_hits_are_real_symbols
- `uv run pytest tests/test_gates.py tests/test_ticket_land.py tests/test_tickets.py -p no:cacheprovider -q`: 216 passed
- `uv run ruff check src/frob/gates/_prework.py tests/test_gates.py` and
  bare `ruff check` (PATH version): both clean
- `uv run ty check src/frob/gates/_prework.py`: clean

Not Filed: T-draft-3efcb40e (never refiled) (app/ticket_runner.py sibling bug),
T-draft-ae3416b9 (never refiled) (SIGINT message / PRE001 catch-22 / scope_digest keying)

Gates: not run via `frob check --ticket T-0240` in this Done report --
REL001 disclosed below.

REL001 disclosure: `frob check --ticket T-0240` (full gate suite) was not
run as part of this implementer pass per the dispatch instructions (do not
run `make coverage`/full gate sweep as a subagent; coordinator stamps
coverage at land). Verification here is the targeted pytest run above plus
`uv run frob ticket evidence T-0240 ...` (which itself runs a full
collect-only pass, succeeded: 3127 python + 145 rust node ids collected)
and the `git diff main --diff-filter=D --stat` deletion-filter check
(empty). `frob check --ticket T-0240` for scope/coverage/waive gates is
left to the coordinator/reviewer per the review-gated flow.
