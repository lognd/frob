## Done report

Changed:
- src/frob/gates/__init__.py::coverage_gate (now takes `root: Path` as its
  first parameter)
- src/frob/gates/__init__.py::_resolved_documented_srcs (new -- symrefs
  with a `frob:doc` edge that actually resolves, via the same
  `_docanchor_check_edge` DOC002 uses)
- src/frob/gates/__init__.py::_cov001 (now takes `root`; uses
  `_resolved_documented_srcs` instead of `_documented_srcs` so a broken
  `frob:doc` edge no longer counts as documentation)
- src/frob/gates/__init__.py::_build_jobs (coverage job now passes
  `st.repo_root`, same root docanchor already uses for T-0314 reasons)
- tests/test_gates.py::TestCoverageGate::test_cov001_broken_doc_edge_does_not_suppress_finding
  (new regression test -- a symbol whose only `frob:doc` edge points at a
  nonexistent anchor now still gets flagged by COV001)
- tests/test_gates.py::TestCoverageGate::test_cov001_passes_when_documented
  and tests/test_gates.py::test_gates_run_gates_integration updated: their
  `frob:doc` fixtures now point at a real anchor in a real doc file under
  `tmp_path`, since a broken target no longer silently satisfies COV001
- tests/test_gates.py, tests/test_tickets_cmd_evidence.py: all
  `coverage_gate(...)` call sites updated for the new `root` parameter

Root cause: `_cov001` decided a symbol was "documented" purely from
`_documented_srcs` (any `frob:doc` EdgeKind.DOC edge existing), never
checking whether that edge's `<file>#<anchor>` target actually resolves.
DOC002 (`docanchor_gate`) already reported the broken edge as its own
error, but the broken edge ALSO satisfied COV001's documentation
obligation for that symbol -- so fixing the DOC002 (giving the edge a
real anchor) was the only way real COV001 gaps on that file surfaced, one
bad line silently masking others. Fix: `_resolved_documented_srcs` reuses
`_docanchor_check_edge`'s own resolution logic (the exact function DOC002
runs) so a symbol only counts as documented when its edge is the same
kind of edge DOC002 would call valid; DOC002 and COV001 can no longer
disagree about what "resolves" means, and neither swallows the other.

Evidence: tests/test_gates.py::TestCoverageGate::test_cov001_broken_doc_edge_does_not_suppress_finding, tests/test_gates.py::TestCoverageGate::test_cov001_passes_when_documented, tests/test_gates.py::test_gates_run_gates_integration -- all 3 confirmed collected via `pytest --collect-only` and passing via `pytest tests/test_gates.py tests/test_tickets_cmd_evidence.py -q` (98 passed) and the full suite (`pytest -q`, all green). `make coverage` ran to completion (exit 0, stamped 407 files).

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-0233` -- 2 errors remain, BOTH out of this
ticket's declared scope (`src/frob/gates/**`, `tests/**`, `tickets.md`),
disclosed rather than force-fixed:
- REL001 (pyproject.toml): `coverage_gate`'s new `root` parameter is a
  public-API-breaking signature change; the version bump this gate wants
  requires editing `pyproject.toml`, which is not in T-0233's scope. Not
  self-expanding scope for this -- flagging for a coordinator/separate
  ticket to bump per REL001's own remedy (`frob release stamp`).
- DRIFT001 (src/frob/gates/__init__.py::coverage_gate sig): the ack for
  this legitimate signature change writes to `frob.lock`, which is also
  outside T-0233's declared scope (confirmed: running `frob ack` clears
  DRIFT001 but trips SCOPE001 on `frob.lock`); reverted that ack rather
  than expand scope. Same tension as REL001 above -- both stem from
  `coverage_gate` gaining a parameter, and both need a scope grant (or a
  follow-up ticket covering `pyproject.toml` + `frob.lock`) to close
  cleanly.
All other gates pass (or are pre-existing waived/unrelated findings, e.g.
`TEST009` design-file e2e counts, `frob-arch` abstraction-opportunity
notes on unrelated test files, `PERF00x` waived findings -- none touched
by this change).
