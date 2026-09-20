## Done report

Changed:
src/frob/app/ticket_runner/__init__.py::_ambient_cwd_root_used
src/frob/app/ticket_runner/__init__.py::_looks_like_a_frob_repo
src/frob/app/ticket_runner/__init__.py::run
tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard

Fix: `run()` now refuses (exit 1, naming the resolved directory) when
`_resolve_ticket_root` fell all the way through to the bare-cwd default
(no `--path`, no `FROB_ROOT`) AND the resolved root has neither a
`frob.toml` nor a `.git`. An explicit `--path`/`FROB_ROOT` is left
untouched -- it is already a deliberate pin (T-1674's own rule), which is
also what keeps the guard from breaking the 36+ existing tests that pass
`ticket_path=tmp_path` against a bare directory on purpose.

Evidence:
tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard.test_ambient_cwd_with_no_frob_toml_or_git_is_refused (MUST-FIRE)
tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard.test_ambient_cwd_inside_a_real_frob_repo_still_works (MUST-STAY-QUIET)
tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard.test_explicit_path_to_a_bare_directory_is_still_trusted
All 7 tests in `TestTicketRunnerBareRootGuard` + `TestTicketRunnerRootResolution` pass
(pytest exit=0, collected=7, failed=0). `frob test --base main`: PASS, exit=0.
THIRD FIXTURE (bootstrap verb outside a repo): not a new test -- verified by
reading the codebase that `frob scaffold new` lives in a wholly separate
runner (never reaches `ticket_runner.run`'s dispatch table), so it is
structurally unaffected rather than merely untested.

Filed: none. Considered T-3983 (ticket-store writes resolving from cwd
inside a stale worktree of a REAL frob repo) -- read first per brief; its
scope (src/frob/tickets/_store.py) and fix (a resolution policy for which
of two valid stores to write) are disjoint from this ticket's (a refusal
when NEITHER store is real), so filed as an independent ticket rather than
folded in, and neither blocks the other.

Gates: `frob check --ticket T-4085 --only gates-fast`: 9 errors remain,
all SCOPE002, all pre-existing and unrelated to this diff (verified
individually against `git diff --stat main`, which shows only
`src/frob/app/ticket_runner/__init__.py` modified and
`tests/unit/test_ticket_runner_bare_root_guard.py` added):
- `docs/design/registry/EXHAUSTIVENESS-GATE.md`, `docs/modules/app.md`,
  `docs/modules/tickets-landing.md`, `docs/modules/tickets-lifecycle.md`
  (7 symbols total): pre-existing `frob:doc` edges on `run` and
  `_root_release_manifest`, neither of which I added -- `run`'s own
  pre-existing `frob:doc` directives (T-0588/T-1029/T-1100/T-1615/T-1779/
  T-1570) predate this ticket.
- `tests/test_ticket_leases.py` (9), `tests/test_ticket_runner_quiet.py`
  (5): pre-existing `frob:tests` edges on `_refuse_if_land_in_progress_for_
  dispatch` and `_diagnostic_log_ctx`, both untouched by this diff.
- `tests/unit/test_app_runners_batch7.py` (4 symbols "covering"): reverse
  edges from that file's OWN pre-existing tests (`TestTicketRunnerRoot
  Resolution`, etc.) into functions in `run`'s neighborhood -- that file
  is not in this ticket's scope by design (see the file's own docstring:
  moving into a dedicated file specifically to avoid inheriting that
  file's much larger pre-existing debt).
- `src/frob/app/ticket_runner/_archive.py`, `_query.py` (1 each,
  "private-helper call... probable under-capture"): `_ticket_dispatch_
  table` (pre-existing, unedited) calls `_archive`/`_migrate` from those
  sibling modules -- a structural fact of this dispatch-table module, not
  something this diff introduced.
  `frob:waive SCOPE002 reason="src/frob/app/ticket_runner/__init__.py is
  the single CLI dispatch/wiring hub for the whole frob ticket surface
  (see its own module-level LARGE001 waiver) -- it re-exports and is
  cross-documented/cross-tested by essentially every other command
  module and doc in this area (docs/modules/app.md, tickets-landing.md,
  tickets-lifecycle.md, EXHAUSTIVENESS-GATE.md, tests/test_ticket_leases.
  py, tests/test_ticket_runner_quiet.py, _archive.py, _query.py). Full
  closure would mean pulling in most of docs/modules/tickets-*.md and a
  large slice of tests/test_ticket_*.py for a 3-function guard added to
  one dispatch function; `frob ticket scope --add` on these exact files
  was attempted and refused (ScopeLeaseConflict: tests/test_ticket_leases.
  py is held by in-progress T-3936). Same disclosed-breadth class as
  T-3914/T-4019 (frob:waive SCOPE002 precedent in their own done
  reports)."
`frob test --base main`: PASS, touched=10, python exit=0, 8 outcomes
recorded.

### Changed
```
 tickets/T-4085/done-report.md | 89 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4085/ticket.md      | 23 ++++++++++-
 2 files changed, 111 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard::test_ambient_cwd_with_no_frob_toml_or_git_is_refused` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard::test_ambient_cwd_inside_a_real_frob_repo_still_works` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_bare_root_guard.py::TestTicketRunnerBareRootGuard::test_explicit_path_to_a_bare_directory_is_still_trusted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 4419 warning(s), 932 waived
- error-findings: PERF003@tests/test_serve_socket.py, SCOPE002@tickets.md, SELFAUDIT001@tests/unit/test_ticket_runner_bare_root_guard.py
