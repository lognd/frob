## Done report

Changed:
- scripts/fleet_status.py:
  - _parse_ticket_frontmatter_text (new): pure-parse half of
    ticket_frontmatter_on_main, split out so the same parser runs
    regardless of which git-show path supplied the text
  - ticket_frontmatter_on_main: now falls back to
    main:tickets/archive/<id>/ticket.md when the active-ledger path
    resolves to nothing (the actual fix for the archived-blocker
    misdiagnosis)
  - _classify_blockers (new, replaces _open_blocker_ids): returns
    (open_ids, unresolved_ids) instead of one merged "still open" list
  - _local_ledger_state, _classify_blockers_local (new): the local-disk
    twin used by _rotting_entry, so TICKET ROT's NEEDS DISPATCH bucket
    agrees with ticket_readiness's dispatchable verdict without a git
    show per blocker on every rot pass
  - _parse_ticket_ledger_fields (new, ARCH001 split off
    _parse_ticket_ledger_file): blocked_by: block parsing added to the
    local ledger parser
  - _rotting_entry: now carries open_blockers/unresolved_blockers
  - _print_ticket_rot: NEEDS DISPATCH excludes any leaf with a
    still-open or unresolved blocker; new "BLOCKED (dependency not yet
    resolved)" bucket reports them instead -- never silently dropped
  - _ticket_dispatchable / ticket_readiness / _ticket_readiness_lines:
    thread unresolved_blockers through as a field distinct from
    open_blockers (acceptance [2]'s own wording), both still gate
    dispatchable
- docs/guides/coordinator-scripts.md: new anchors for every function
  above; _print_ticket_rot's own section documents the T-1696 incident
  and the BLOCKED bucket split
- tests/unit/test_coordinator_scripts.py: 16 new tests across
  TestClassifyBlockers, TestClassifyBlockersLocal,
  TestTicketFrontmatterOnMain (archive-fallback), TestRottingTickets (2:
  reproduces T-1696's exact shape + a must-still-block control),
  TestPrintTicketRot (2: BLOCKED bucket split, unresolved-also-excludes)

DESIGN DECISION -- no `import frob` (addressing the coordinator's own
question directly): `scripts/fleet_status.py`'s module docstring states
a load-bearing "no frob import" contract, restated at three separate
call sites in the file (QUARANTINE/VERIFY_QUEUE comments,
ticket_frontmatter_on_main's own docstring) -- the script must run
correctly under ANY python3 on PATH, not only this project's own built
venv, per `scripts/_require_python.py`'s own module docstring ("this
module itself must run under ANY python3 on PATH ... including one far
older than the project requires"). `uv run python scripts/
fleet_status.py` (the coordinator's own invocation) happens to use a
venv with frob installed, but that is incidental to what the guard
actually checks (interpreter VERSION, not package availability) -- it
is not evidence the "no frob import" contract was meant to be relaxed.
Implemented instead: `_classify_blockers`/`_classify_blockers_local`
mirror `frob.tickets.load_queue`'s exact two-location resolution order
(active ledger, then archive) in plain form, matching the SEMANTIC
behavior `tests/test_ticket_land.py::TestArchiveV2::
test_archived_v2_ticket_still_resolves_as_blocker` pins for the real
resolver, without importing it.

Root cause: `ticket_frontmatter_on_main` only ever read `main:tickets/
<id>/ticket.md`; a completed-and-archived ticket's file lives at
`main:tickets/archive/<id>/ticket.md` instead, so it resolved to
nothing, and `_open_blocker_ids` (the old name) treated "cannot
resolve" as "still open" -- the two facts (genuinely open vs.
unresolvable) were never distinguished. Separately, `_print_ticket_rot`'s
NEEDS DISPATCH bucket never consulted blocked_by AT ALL (it only split
by tier/runs_last), so a still-blocked leaf and a genuinely dispatchable
one were indistinguishable in that section regardless of the
`ticket_frontmatter_on_main` fix -- acceptance [3] needed that second,
independent fix (blocker classification piped into `_rotting_entry`,
then filtered in `_print_ticket_rot`) to close, not just the archive
fallback.

Verification: `uv run pytest tests/unit/test_coordinator_scripts.py`
135/135 passed (16 new + 119 pre-existing, all still green). `uv run
frob check --budget 500 --ticket T-2449` -- 0 errors on every file this
ticket touched (JSON diagnostic file-path filtering), across 3
iterations fixing a real COV005 directive-attachment defect I introduced
(inserting a new comment block immediately adjacent to an existing one,
with no blank-line separator, caused the OLD block's frob:ticket/frob:doc
lines to misattach to my new function -- fixed by restoring the blank-
line boundary and removing a stray duplicate), a real ARCH001 (my
blocked_by-parsing addition pushed _parse_ticket_ledger_file over 60
lines, fixed by the _parse_ticket_ledger_fields split), and a ruff
E501.

A live `uv run python scripts/fleet_status.py --ticket T-1696` (the
ticket named in this bug's own measurement) no longer reproduces the
exact incident, because T-1696 itself resolved to `state: done` on
`main` sometime during this session (a real land, unrelated to this
fix) -- the synthetic reproduction in
`TestRottingTickets::test_archived_done_blockers_do_not_keep_a_ticket_permanently_blocked`
(exact blocker-id/archived-state shape T-1696 had) is what this Done
report's acceptance [0]/[3] evidence actually stands on.

Filed: none (no out-of-scope work found).

Gates: `frob check --budget 500 --ticket T-2449` -- 0 errors on every
file this ticket changed.

### Changed
```
 tickets/T-2449/ticket.md | 48 +++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 43 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_archived_done_blockers_do_not_keep_a_ticket_permanently_blocked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_archived_done_blocker_is_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_done_archived_blocker_is_closed` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_falls_back_to_archive_when_active_ledger_has_no_such_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_a_genuinely_open_blocker_still_blocks` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_in_progress_blocker_is_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_queued_blocker_is_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestClassifyBlockers::test_missing_blocker_is_unresolved_not_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestClassifyBlockersLocal::test_missing_blocker_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_blocked_leaf_never_appears_under_needs_dispatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_unresolved_blocker_also_keeps_leaf_out_of_needs_dispatch` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2449/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2449/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2449/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2449/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2449/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2449, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
