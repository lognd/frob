---
id: T-2221
title: 'Every agent''s pytest claims the whole machine: -n auto oversubscribes ~4x
  under a multi-agent fleet (load 28 on 12 CPUs)'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/config.py
- src/frob/tickets/_worktree_guard.py
- tests/test_worktree_guard.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: 'Measured: neither in-scope file (_verify.py, config.py) has a pytest spawn
    affected by -n auto -- _verify.py:1467''s only pytest spawn already overrides
    addopts entirely (-o addopts=), never resolving xdist auto at all. The one real
    cross-agent choke point is agent_env_exports() in _worktree_guard.py: it is the
    SAME env-injection function frob agent env already uses to export FROB_WORKTREE/FROB_AGENT
    into a dispatched agent''s shell (playbook sec 1b), inherited by every downstream
    pytest spawn (raw shell AND frob-spawned) without duplicating the rule per call
    site. read_all_leases() in the same package already provides the real, non-ps
    cross-worktree concurrency signal doable() uses.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_worktree_guard.py
  reason: 'Measured: neither in-scope file (_verify.py, config.py) has a pytest spawn
    affected by -n auto -- _verify.py:1467''s only pytest spawn already overrides
    addopts entirely (-o addopts=), never resolving xdist auto at all. The one real
    cross-agent choke point is agent_env_exports() in _worktree_guard.py: it is the
    SAME env-injection function frob agent env already uses to export FROB_WORKTREE/FROB_AGENT
    into a dispatched agent''s shell (playbook sec 1b), inherited by every downstream
    pytest spawn (raw shell AND frob-spawned) without duplicating the rule per call
    site. read_all_leases() in the same package already provides the real, non-ps
    cross-worktree concurrency signal doable() uses.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'Measured: neither in-scope file (_verify.py, config.py) has a pytest spawn
    affected by -n auto -- _verify.py:1467''s only pytest spawn already overrides
    addopts entirely (-o addopts=), never resolving xdist auto at all. The one real
    cross-agent choke point is agent_env_exports() in _worktree_guard.py: it is the
    SAME env-injection function frob agent env already uses to export FROB_WORKTREE/FROB_AGENT
    into a dispatched agent''s shell (playbook sec 1b), inherited by every downstream
    pytest spawn (raw shell AND frob-spawned) without duplicating the rule per call
    site. read_all_leases() in the same package already provides the real, non-ps
    cross-worktree concurrency signal doable() uses.'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_worktree_guard.py::TestAgentEnvExports::test_fleet_context_bounds_xdist_workers
- tests/test_worktree_guard.py::TestAgentEnvExports::test_no_fleet_context_omits_xdist_bound
designated_repro_test: null
acceptance:
- text: 'A pytest spawned under agent/fleet context receives a bounded PYTEST_XDIST_AUTO_NUM_WORKERS
    (fails today: nothing sets it)'
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvExports::test_fleet_context_bounds_xdist_workers
- text: A pytest spawned with NO fleet context MUST STILL resolve auto to full CPU
    count -- must-still-pass control for the single-developer path
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvExports::test_no_fleet_context_omits_xdist_bound
- text: The bound derives from a real concurrency signal (lease count or coordinator-set
    var), never a hardcoded constant and never parsed from ps output
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvExports::test_fleet_context_bounds_xdist_workers
- text: Set at a single choke point; if none exists, report the five-spawn-site finding
    rather than silently duplicating the rule
  evidence:
  - tests/test_worktree_guard.py::TestAgentEnvExports::test_fleet_context_bounds_xdist_workers
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# Every agent's pytest claims the whole machine: `-n auto` oversubscribes ~4x under a multi-agent fleet

## Measured evidence (2026-08-16)

    nproc = 12
    pyproject.toml addopts = "-q -n auto --dist=loadgroup --timeout=120 ..."

`-n auto` resolves to the CPU count of the machine. It means "auto for a
machine I own ALONE". Under this repo's normal operating mode -- a coordinator
running 4+ implementer agents in parallel worktrees -- every agent
independently resolves `auto` to 12 and requests 12 workers. Four concurrent
agents therefore request ~48 workers on 12 cores.

Observed directly, with 4 agents live:

    LOAD 28.2   MEM 10.5GB avail   (12 CPUs)

    per-worktree process counts:
      t-2207  174
      t-2107   17
      t-2205   11
      t-2208    8

Nothing is broken; everything is simply ~4x slower than it needs to be.
Measured land cadence during this window was ~12 min/land against a 5 min
target, and the coordinator has been holding dispatch at 4 agents citing
load -- so the oversubscription is directly capping fleet throughput.

## The mechanism (verified, not assumed)

`pytest-xdist` 3.8.0 reads an env var when resolving `auto`:

    .venv/.../xdist/plugin.py:17
        env_var = os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS")

This is the right lever precisely because it **redefines what `auto` means**
rather than removing `-n auto` from addopts. That matters: T-2068 (queued) is
about the retry path being unable to neutralise `addopts -n auto`, and T-2032
(done) records that appending `-p no:xdist` without removing `-n` dies with a
usage error. Fighting addopts is a known-bad path in this repo. Setting the
env var sidesteps all of it and composes with the existing `-o addopts=""`
override where that is already used (`_verify.py:1467`).

## Do NOT fix it this way

- **Do NOT edit `addopts` in pyproject.toml to a fixed `-n 3`.** That
  penalises the single-developer case, which SHOULD use the whole machine.
  The worker count must depend on how many agents are actually running, not
  on a constant checked into the repo.
- **Do NOT remove `-n auto` or add `-p no:xdist`.** T-2032 already recorded
  that this produces a usage error, and it is the exact wall T-2068 is stuck
  on. Redefine `auto`; do not fight it.
- **Do NOT put this in the agent brief / playbook.** Telling agents to export
  a variable is precisely the "warn them harder" non-fix this repo's standing
  audit duty forbids -- four agents warned about the confirmatory-evidence
  trap all still fell in. It must be set by the tool that spawns pytest.
- **Do NOT infer the agent count by parsing `ps` output.** Process-counting
  has already produced a 4x miscount in this repo ("15-16 concurrent lands"
  when there were 4, because `ps aux | grep -c` counts ~4 lines per land).
  Use a real signal -- the lease count, or an explicit env var the
  coordinator sets when it dispatches.

## Acceptance criteria

1. (MUST FAIL FIRST) A test asserting that a pytest spawned under the
   fleet/agent condition receives a bounded `PYTEST_XDIST_AUTO_NUM_WORKERS`
   in its environment. Fails today: nothing sets it anywhere. Confirm
   `--check-repro` reads FAILED_AT_PARENT before the fix commit.
2. A pytest spawned with NO agent/fleet context MUST STILL resolve `auto` to
   the full CPU count -- the single-developer path is not degraded. This is
   the must-still-pass control; without it a fix that simply always caps
   workers scores identically.
3. The bound is derived from a real concurrency signal (lease count or an
   explicit coordinator-set variable), not a hardcoded constant and not
   parsed from `ps`.
4. Whatever central point frob uses to build a pytest invocation sets it
   once. If the implementer finds there is NO single choke point -- the
   candidate spawn sites are `_verify.py:1467`, `_cli_parsers/_core.py:162`,
   `gates/_fix_engine_tier_b.py:388`, `perf_runner.py:55`,
   `mutate_runner.py:40` -- then report that as the finding and fix the
   agent-facing test path first rather than touching all five. Five homes for
   one rule is the defect shape T-1966 covers; say so explicitly rather than
   silently duplicating.

## Relationship to existing tickets

- T-2068 (queued): retry path cannot neutralise `addopts -n auto`. SAME root
  mechanism, different symptom. If the implementer picks up both, the env-var
  approach here may make T-2068 substantially easier -- but do NOT close
  T-2068 from this ticket; they are separately verifiable.
- T-2032 (done), T-1824: prior art on why removing `-n` breaks.

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
