## Done report

`frob check` reprints a prior verdict automatically instead of recomputing
when the tree has not moved. `_run_gates` (`frob.check._python`) now
fingerprints the tree via `root_content_key` (T-1445) folded with a digest
of `.frob/baseline`'s bytes, and looks up a stored `ToolResult` list keyed
by the exact request signature (`gates` subset, `ticket`, `base`, `delta`)
via two new primitives in `frob.gates._gate_cache`: `load_gate_run_replay`
/ `store_gate_run_replay`, backed by a new `run_replay` table in the
existing `.frob/gate-cache.db` (same file T-0602/T-1445 already own, no
parallel cache). On a hit, the prior findings are reprinted byte-for-byte
identical, with only the trailing `gate-summary` line's TEXT prefixed
`[REPLAY age=Ns]` so a reprint is never visually indistinguishable from a
fresh run. No flag, no caller obligation, matching the owner's explicit
rejection of a `--last`-style flag.

The correctness guard: the request signature (`gates`/`ticket`) is part of
the storage KEY itself, not inspected after a hit. A `--only <group>` /
`--budget`-chunked call always requests a non-empty `gates` subset and is
stored `partial=True`; a `--ticket`-scoped call is keyed on that ticket.
Neither can ever satisfy a later full/unscoped lookup (`gates=frozenset()`,
`ticket=None`) -- that lookup asks a different question at a different
key, so an incomplete prior run's entry is structurally unreachable from a
complete request, never merely disclosed-but-trusted.

Manually verified (in addition to the bound pytest evidence) against the
real repo tree, `--only tickets`:
- unchanged tree: first run 50.1s, second run 0.24s, identical findings,
  `[REPLAY age=0.3s]` on the summary line only.
- `--ticket T-2585`-scoped run followed by an unscoped run: the unscoped
  run was NOT served by the scoped run's entry (it independently hit an
  earlier real unscoped entry from a prior manual run, confirmed by its
  own distinct age).
- tracked-file edit (README.md) between two identical-signature calls:
  second call recomputed for real, no `[REPLAY]` tag.

## Changed

- `src/frob/gates/_gate_cache.py` -- `GateRunReplay`, `load_gate_run_replay`,
  `store_gate_run_replay`, `_replay_signature`, `_replay_fingerprint`,
  `_REPLAY_SCHEMA` (new `run_replay` sqlite table).
- `src/frob/check/_python.py` -- `_run_gates` now checks/stores a replay
  around its `run_gates` call; new `_label_replay` helper; added a module
  logger (`_log`) that did not previously exist in this file.
- `docs/modules/serve.md` -- new "Whole-run replay (T-2585)" subsection
  documenting the mechanism, the rejected-flag rationale, and the
  signature+fingerprint safety property.
- `tests/test_gate_cache.py` -- `TestRunReplay` (4 tests): unchanged-tree
  replay, tracked-edit forces a real run, budget-clipped/`--only`-scoped
  prior run never replays as complete (the ticket's own must-have
  control), ticket-scoped prior does not serve an unscoped lookup.

## Evidence

- `tests/test_gate_cache.py::TestRunReplay::test_unchanged_tree_replays`
- `tests/test_gate_cache.py::TestRunReplay::test_tracked_edit_forces_real_run`
- `tests/test_gate_cache.py::TestRunReplay::test_budget_clipped_prior_run_never_replays_as_complete`
  (designated repro: `FAILED_AT_PARENT` at 835e89007, per BUG002)
- `tests/test_gate_cache.py::TestRunReplay::test_ticket_scoped_prior_does_not_serve_unscoped`

`pytest tests/test_gate_cache.py -q`: 35 collected, 0 failed (31 pre-existing
+ 4 new).

## Filed (out of scope, found while working T-2585)

- T-2608 -- gate:SCOPE002 closure debt: any ticket that scopes
  narrowly to `src/frob/gates/_gate_cache.py` and/or `src/frob/check/
  _python.py` alone trips 850+ PRE-EXISTING scope-closure warnings the
  moment its scope is queried/extended, because these two files' existing
  (pre-T-2585) public symbols document into `docs/modules/gates.md` and
  ~20 test files never in scope. Confirmed pre-existing via `git show
  HEAD:<file>` before this ticket's own edits. Not fixed here -- a design
  decision (splitting doc anchors, or changing closure-warning semantics)
  outside a bug-fix ticket's scope.
- T-2610 -- WIRE001's resolver follows call-expression syntax
  only, so a genuinely-called `@property` (read via plain attribute
  access, e.g. `replay.age_s` in `_label_replay`) reads as unwired.
  Waived narrowly on `GateRunReplay.age_s` with this ticket as follow_up.

## Gates

`uv run frob check --ticket T-2585`: zero unwaived findings attributable
to any file this ticket touched (`_gate_cache.py`, `_python.py`,
`docs/modules/serve.md`, `tests/test_gate_cache.py`), verified by grep
across the full unfiltered log for each of those four paths after every
fix round. Remaining FAILs in the overall tool summary (`gate:PERF`,
`gate:SEC`, `gate:SELFAUDIT`, `gate:TICK`, `ruff-format` repo-wide drift,
etc.) are pre-existing, repo-wide, and independently confirmed to name
files this ticket never touched -- expected per playbook section 6c
(`--ticket` narrows only SCOPE/PREWORK/COV002/TODO001/FMT/AFFECT; every
other family's count is repo-wide). `gate:SCOPE`'s 852 SCOPE002 warnings
(warning-level, not errors) are the pre-existing closure debt filed as
T-2608 above; the one SCOPE001 error is `tickets/T-draft-.../
ticket.md` outside T-2585's own scope, an artifact of filing that residue
ticket from inside this worktree.

### Changed
```
 docs/modules/serve.md              |  52 +++++++++
 src/frob/check/_python.py          |  53 ++++++++-
 src/frob/gates/_gate_cache.py      | 215 +++++++++++++++++++++++++++++++++++++
 tests/test_gate_cache.py           | 145 +++++++++++++++++++++++++
 tickets/T-2585/ticket.md           |  13 ++-
 tickets/T-2608/ticket.md |  95 ++++++++++++++++
 tickets/T-2610/ticket.md |  52 +++++++++
 7 files changed, 621 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gate_cache.py::TestRunReplay::test_unchanged_tree_replays` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunReplay::test_tracked_edit_forces_real_run` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunReplay::test_budget_clipped_prior_run_never_replays_as_complete` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunReplay::test_ticket_scoped_prior_does_not_serve_unscoped` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH102@src/frob/tickets/_doable.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2585/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2585/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2585, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
