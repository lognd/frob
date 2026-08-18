## Done report

Changed:
- src/frob/app/ticket_runner/_query.py (_contention, _compute_contention,
  ContentionEntry, ContentionOutcome, _suggested_contention_batches,
  _render_contention_json, _render_contention_plain, _hot_files_for_tickets,
  _doable_row hot-file marker, _render_doable_dispatchable/_render_doable_plain
  threading)
- src/frob/app/ticket_runner/__init__.py (dispatch table + read-only
  allowlist wiring for "contention")
- src/frob/_cli_parsers/_ticket/_query.py (`contention` subcommand parser)
- tests/unit/test_app_runners_t2395_contention.py (new)

Evidence: 6 pytest node ids bound to acceptance #1 (see ledger), all
passing locally (SUITE-RESULT: exitstatus=0 collected=6 failed=0).

Design notes: `_compute_contention` matches declared scope against the
git-tracked file universe (`scope_breadth_context`/`_repo_files`, the
same fast substrate T-0453's breadth/lease checks already use) rather
than the filesystem-globbing `_expand_scope_globs_to_paths` `frob
ticket new`'s own overlap warning uses -- an early version reused that
helper directly and measured `frob ticket doable` exceeding 100s per
call on this repo's real ticket count (it re-walks the filesystem once
per open ticket AND picks up derived noise like __pycache__/*.pyc under
a broad src/** glob). Switching to fnmatch-over-`git ls-files` fixed
both: one `git ls-files` spawn total, tracked source only.

FAIL-LOUDLY (T-2391): `contention` with zero contended files prints an
explicit "zero contention: no file is declared by 2+ currently-open
tickets" line, never silence.

Automatic-over-commands: `frob ticket doable`'s plain render now
appends a `[HOT FILE: <path> (Nx open tickets) -- run frob ticket
contention before dispatching]` marker on any returned row that sits on
a contended file, computed from the same breadth pass `doable` already
does (no extra git spawn).

Filed (out-of-scope discoveries, not touched here):
- T-2444: pre-existing SystemExit failures in
  tests/unit/test_app_runners_t1738_wave.py (2 tests) caused by an
  unrelated duplicate-title refusal now firing on that test's own `_new`
  helper -- reproduced against a clean worktree with none of this
  ticket's changes present, confirmed NOT a regression from this ticket.

Gates: pytest tests/unit/test_app_runners_t2395_contention.py 6/6 pass
locally. Full `frob check`/`frob test` not run standalone by this agent
(playbook section 3b budget rules) -- `frob ticket land` runs its own
gate pass; see the LAND-PROOF line for the authoritative result.

### Changed
```
 src/frob/_cli_parsers/_ticket/_query.py         |  12 +
 src/frob/app/ticket_runner/__init__.py          |   5 +
 src/frob/app/ticket_runner/_query.py            | 305 +++++++++++++++++++++++-
 tests/unit/test_app_runners_t2395_contention.py | 162 +++++++++++++
 tickets/T-2395/ticket.md                        |  17 +-
 5 files changed, 493 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_plain_render_ranks_and_names_owners` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_zero_contention_is_explicit_not_silent` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_json_render_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_suggested_batching_is_transitive_across_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker::test_doable_row_carries_hot_file_marker` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker::test_doable_row_has_no_marker_without_contention` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/ticket_runner/_query.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DUP001@src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2395/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2395/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2395/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2395/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2395, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
