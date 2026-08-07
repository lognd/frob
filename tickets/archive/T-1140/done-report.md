## Done report

Extracted the TICK00x ledger-hygiene/invariant family (tickets_gate and
its ten _tickN_* private helpers, T-0162/T-0409/T-0411/T-0537/T-0726/
T-0820/T-0842/T-0714) out of gates/__init__.py into a new
gates/_tickets_gate.py, one-family-per-land (T-1072/T-1077/T-1115
discipline): verbatim move, directives intact, imports re-homed
(module-level where cheap, or a lazy call-time import back to
frob.gates for on_default_branch specifically, so the pre-existing
monkeypatch("frob.gates.on_default_branch", ...) test target keeps
resolving -- the same pattern gates/_debt_deprecated.py already uses
for its own call-back-to-frob.gates cases).

Repo-wide grep confirmed only `tickets_gate` (the public gate function),
`_tick004_queue_rot`, and `on_default_branch` are imported/patched
directly from `frob.gates` by anything outside gates/__init__.py itself
(tests/test_tickets_priority.py, tests/test_tickets_collision.py) --
all three are re-exported from gates/__init__.py with a noqa: F401 and
a one-line reason each; every other _tickN_* helper stays private to
the new module.

docs/modules/gates.md's five `frob:describes
src/frob/gates/__init__.py::_tickNNN_*` doc anchors were repointed to
`src/frob/gates/_tickets_gate.py::_tickNNN_*` (docanchor/doclink pass
clean after the repoint).

The move broke three `frob:tests` directives in
tests/test_tickets_collision.py (DRIFT002: symref
src/frob/gates/__init__.py::tickets_gate no longer resolves) -- fixed by
repointing them to gates/_tickets_gate.py::tickets_gate; this pulled
tests/test_tickets_collision.py into T-1140's scope (`frob ticket
scope T-1140 --add`, reasoned) since T-1140's original scope only
listed tests/test_gates.py.

gates/__init__.py: 9172 -> 8408 lines (still above the 800-line
acceptance threshold -- this is one family of the ~13 named in the
ticket body, not the full split). Requeuing the remaining families
(SCOPE/PREWORK, INV00x, TEST00x, DECISIONS, COMPLIANCE00x, SYS00x/
DOC00x, DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates
spine, COV00x) as residue -- this round's budget covered exactly the
TICK00x family (follow-up filed and landed as T-1159).

Verification: ruff check clean on both files (both `ruff` and
`uv run ruff`). All TICK-family tests pass (tests/test_gates_tick005.py,
tests/test_gates_tick009_tick010.py, tests/test_gates_tickets_hygiene.py,
tests/test_tickets_priority.py, tests/test_tickets_collision.py --
39 passed). frob check --ticket T-1140 --only drift is clean (0 errors)
after the symref repoint. frob check --ticket T-1140 --only coverage
has 24 pre-existing errors (COV003 stale rust evidence ids on
T-0138/T-0226/T-0629/T-0700/T-0702, COV006/COV007 on unrelated
src/frob/tickets/__init__.py, src/frob/serve/_daemon.py etc.) --
confirmed identical count/content before this change by diffing
against a HEAD-checked-out gates/__init__.py, none reference tickets_gate
or _tickets_gate.py.

Filed: none.

### Changed
```
 docs/modules/gates.md           |  10 +-
 src/frob/gates/__init__.py      | 774 +-------------------------------------
 src/frob/gates/_tickets_gate.py | 797 ++++++++++++++++++++++++++++++++++++++++
 tests/test_tickets_collision.py |   7 +-
 tickets.md                      |   3 +-
 5 files changed, 815 insertions(+), 776 deletions(-)
```

### Evidence
- `tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors` (pytest node id, verified passing when recorded)
- `tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_precisely_scoped_ticket_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags` (pytest node id, verified passing when recorded)
- `tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_draft_id_on_default_branch_is_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 22 error(s), 936 warning(s), 428 waived
- error-findings: AFFECT001@src/frob/gates/_tickets_gate.py, ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1140, SELFAUDIT001@design
