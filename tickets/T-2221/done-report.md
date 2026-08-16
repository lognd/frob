## Done report

Measured: within the declared scope (src/frob/app/ticket_runner/_verify.py,
src/frob/app/config.py), the only pytest spawn is `_run_pytest_directly`
(_verify.py:1467), and it already passes `-o addopts=`, fully overriding
`addopts` -- it never resolves `-n auto` at all and was never part of this
bug. The five candidate spawn sites named in the ticket also include
`_cli_parsers/_core.py:162`, which on inspection is `_PARSE_TOOL_CHOICES`
(an unrelated string list, not a pytest spawn) -- a stale line reference.
A `git grep '"pytest"' -- src/frob` search found well over a dozen actual
pytest-spawn sites scattered across the tree (mutate_runner.py, perf_runner.py,
gates/_fix_engine_tier_b.py, gates/_mutation_evidence.py, testing/_collect.py,
tickets/_evidence.py, tickets/_mutation_evidence.py, refactor/_verify.py, ...).
There is NO single choke point among the pytest-spawn call sites themselves --
confirming acceptance 4's finding branch.

The real single choke point is upstream of all of them: `agent_env_exports()`
in `src/frob/tickets/_worktree_guard.py`, the function `frob agent env`
already uses (T-0574) to export `FROB_WORKTREE`/`FROB_AGENT` into a
dispatched agent's shell environment. Every pytest spawned from that shell
-- an agent's own raw `uv run pytest`, or any frob-internal subprocess spawn
that does not itself override `addopts` -- inherits whatever env is exported
there, so bounding `PYTEST_XDIST_AUTO_NUM_WORKERS` at this ONE point covers
every downstream spawn without duplicating the rule per call site.

Scope was widened (measured reason recorded via `frob ticket scope --add`)
to `src/frob/tickets/_worktree_guard.py`, `tests/test_worktree_guard.py`,
`docs/modules/tickets-data-storage.md` -- the two originally declared files
have no code path this bug actually reaches.

Implementation: `_bounded_xdist_workers(root)` derives the bound from
`len(read_all_leases(root))` -- the real, cross-worktree lease side-channel
`frob.tickets._doable.doable()` already uses to see other live agents,
never `ps`-parsed. Zero other live leases (no fleet context) -> nothing is
exported, so `-n auto` resolves against xdist's own default (full CPU
count) -- the must-still-pass single-developer control, verified by
`test_no_fleet_context_omits_xdist_bound`. One or more other live leases ->
`max(1, cpu_count // (existing + 1))`, treating this agent as one more
claimant alongside the existing leases -- verified by
`test_fleet_context_bounds_xdist_workers` (3 other live leases -> a bound
well under the raw CPU count).

Repro discipline: `test_fleet_context_bounds_xdist_workers` committed alone
first (62094afa5); `frob ticket evidence T-2221 --check-repro ... --base-ref
62094afa5` read FAILED_AT_PARENT before the fix commit (41a507d51) was
added.

Changed:
  src/frob/tickets/_worktree_guard.py::PYTEST_XDIST_AUTO_NUM_WORKERS_ENV
  src/frob/tickets/_worktree_guard.py::_bounded_xdist_workers
  src/frob/tickets/_worktree_guard.py::agent_env_exports
  tests/test_worktree_guard.py::TestAgentEnvExports.test_no_fleet_context_omits_xdist_bound
  tests/test_worktree_guard.py::TestAgentEnvExports.test_fleet_context_bounds_xdist_workers
  tests/test_worktree_guard.py::_write_lease
  docs/modules/tickets-data-storage.md (new subsection)

Evidence:
  tests/test_worktree_guard.py::TestAgentEnvExports::test_fleet_context_bounds_xdist_workers (accepts 0, 2, 3)
  tests/test_worktree_guard.py::TestAgentEnvExports::test_no_fleet_context_omits_xdist_bound (accepts 1)
  Full tests/test_worktree_guard.py run: 21 passed (uv run pytest tests/test_worktree_guard.py -q)

Filed: none -- no out-of-scope work discovered beyond the stale
line-reference in the ticket's own candidate list (reported above, not
filed as a ticket).

Gates: gate:FMT/gate:test/gate:DRIFT/gate:gates-native/gate:gates-security
chunks all clean for this ticket's own files (`frob check --only <group>
--ticket T-2221`, and full unscoped chunk runs via `--stamp-baseline`).
The only unscoped ERROR-level findings observed anywhere in the tree
(ruff E501 in src/frob/lang/_nodes.py, F541 in
tests/test_ticket_work_and_land_finish.py; 3 DRIFT001 digest-moved findings
in _land_cmd.py/_rapid_sweep.py/lang/_nodes.py) are PRE-EXISTING on `main`
itself after merging -- `git diff main --stat` for every one of those files
is empty; not touched by this ticket, not introduced by it.
`git diff main --diff-filter=D --stat` is empty (no deletions).

### Changed
```
 docs/modules/tickets-data-storage.md | 32 ++++++++++++++
 src/frob/tickets/_worktree_guard.py  | 81 ++++++++++++++++++++++++++++++++----
 tests/test_worktree_guard.py         | 71 +++++++++++++++++++++++++++----
 tickets/T-2221/ticket.md             | 60 +++++++++++++++++++++++---
 4 files changed, 224 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestAgentEnvExports::test_fleet_context_bounds_xdist_workers` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvExports::test_no_fleet_context_omits_xdist_bound` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2221/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2221/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2221, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
