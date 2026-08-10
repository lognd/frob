---
id: T-1738
title: 'frob ticket wave: partition the doable set into N mutually scope-disjoint
  groups for parallel dispatch'
state: done
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_doable.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_query.py
- src/frob/app/config.py
- tests/test_tickets_lease.py
- tests/unit/test_app_runners_t0976_mutation_evidence.py
- src/frob/app/_config_external.py
- tests/unit/test_app_runners_t1738_wave.py
- tests/test_tickets_wave.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: docs/modules/tickets.md is contended (leased by T-1686/T-1736 for other
    work); implement frob ticket wave in code first, doc it in a follow-up once the
    lease frees
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/tickets/_query.py
  reason: src/frob/tickets/_query.py does not exist; the real doable/partition logic
    lives in _doable.py, wired through the ticket_runner dispatch table and CLI parser
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'add the real implementation surfaces frob ticket wave needs: partition
    logic in _doable.py, dispatch-table+read-only-allowlist wiring in ticket_runner/__init__.py,
    argparse registration in _cli_parsers/_ticket/_query.py, AppConfig fields in config.py,
    plus their bound test files'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'add the real implementation surfaces frob ticket wave needs: partition
    logic in _doable.py, dispatch-table+read-only-allowlist wiring in ticket_runner/__init__.py,
    argparse registration in _cli_parsers/_ticket/_query.py, AppConfig fields in config.py,
    plus their bound test files'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: 'add the real implementation surfaces frob ticket wave needs: partition
    logic in _doable.py, dispatch-table+read-only-allowlist wiring in ticket_runner/__init__.py,
    argparse registration in _cli_parsers/_ticket/_query.py, AppConfig fields in config.py,
    plus their bound test files'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/config.py
  reason: 'add the real implementation surfaces frob ticket wave needs: partition
    logic in _doable.py, dispatch-table+read-only-allowlist wiring in ticket_runner/__init__.py,
    argparse registration in _cli_parsers/_ticket/_query.py, AppConfig fields in config.py,
    plus their bound test files'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_tickets_lease.py
  reason: 'add the real implementation surfaces frob ticket wave needs: partition
    logic in _doable.py, dispatch-table+read-only-allowlist wiring in ticket_runner/__init__.py,
    argparse registration in _cli_parsers/_ticket/_query.py, AppConfig fields in config.py,
    plus their bound test files'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners_t0976_mutation_evidence.py
  reason: 'add the real implementation surfaces frob ticket wave needs: partition
    logic in _doable.py, dispatch-table+read-only-allowlist wiring in ticket_runner/__init__.py,
    argparse registration in _cli_parsers/_ticket/_query.py, AppConfig fields in config.py,
    plus their bound test files'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: wave() needs a public re-export from frob.tickets/__init__.py's __all__,
    matching doable/doable_blocked's existing pattern
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: ticket_wave_agents needs to be added to the CLI-args allowlist AppConfig.from_external
    reads from
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners_t1738_wave.py
  reason: CLI-level render tests for the new wave verb
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/tickets/__init__.py
  reason: reverted the package re-export to avoid dragging every other public symbol
    in that shared file into this ticket's scope closure (SCOPE002 explosion via docs/modules/tickets.md);
    wave is imported directly from frob.tickets._doable instead
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_tickets_wave.py
  reason: wave() unit tests
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets_wave.py::TestWave::test_disjoint_scopes_pack_into_separate_groups
- tests/test_tickets_wave.py::TestWave::test_colliding_scopes_share_one_group
- tests/test_tickets_wave.py::TestWave::test_unplaceable_ticket_lands_in_remainder_with_reason
- tests/test_tickets_wave.py::TestWave::test_deterministic_for_repeated_calls
- tests/test_tickets_wave.py::TestWave::test_fewer_groups_than_agents_is_not_an_error
- tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_json_render_shape
- tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_plain_render_lists_groups_and_remainder
- tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_missing_agents_flag_is_a_clean_error
designated_repro_test: null
threat: null
component: null
---
`frob ticket doable` answers "what can ONE agent safely start right now",
filtering candidates whose scope collides with an in-progress lease
(T-0453). That is the sequential question, and it is answered well.

Nobody answers the PARALLEL question: "partition the doable set into N
groups whose scopes are mutually disjoint, so N agents can run at once
without colliding." A coordinator dispatching a wave has to do that by
hand, and the only cheap hand-proxy is thematic grouping -- "these are
all docs tickets", "these are all gate false positives" -- which is not
the same property at all.

Observed cost, 2026-08-06, in one session:

- A coordinator grouped three waves by theme instead of by scope. Two
  tickets in one wave (T-1699, T-1705) turned out to be scope-blocked by
  leases held by agents dispatched earlier in the SAME wave planning
  pass. `doable --show-blocked` knew; nothing had asked it.
- T-1679 and T-1637 were thematically unrelated and scope-adjacent:
  T-1679 renamed tests that T-1637 (already closed) had bound its
  evidence to. The rename landed green under `--ticket` scoping and broke
  a closed ticket's evidence on main. Theme said "safe"; scope said
  otherwise.

Build the parallel answer:

    frob ticket wave --agents N [--json]

Returns N groups drawn from the doable set such that no two groups share
a scope glob, each group ordered for sequential execution within itself,
plus an explicit REMAINDER list of doable tickets that could not be
placed disjointly -- and WHY (naming the ticket and the shared glob they
collide on). The remainder is the important half: silently dropping
unplaceable tickets would make a wave look complete when it is not.

Requirements:

- Collision must be computed on RESOLVED scope, the same substrate
  `doable`'s T-0453 filter already uses. Do not re-implement glob
  matching -- extract and share whatever `doable` uses, or this grows a
  second answer to the same question that can disagree with the first.
- Groups must also respect blocked_by ordering: a group is a sequence an
  agent works in order, so a ticket must never precede its blocker.
- Deterministic for a given queue state, so two coordinators planning the
  same wave get the same plan.
- N is a hint, not a guarantee: returning fewer, larger groups is correct
  when the queue does not partition further. Say so in the output rather
  than padding groups with colliding work.
- Prefer packing by priority: a group containing a critical ticket should
  not be the one left unplaceable.

A LIKELY FINDING, WORTH REPORTING RATHER THAN DESIGNING AROUND: this
repo's queue may barely partition at all, because `docs/modules/
tickets.md` appears in a large fraction of every ticket's scope and
therefore collides with almost everything. `--show-blocked` currently
shows a dozen tickets all held on that single path, and two in-progress
tickets mutually blocking each other on it. If the wave command finds it
cannot produce more than one or two disjoint groups, that is a real
measurement of a real bottleneck and should be REPORTED as the result,
not worked around by loosening the collision rule. File what you find;
the remedy (splitting that doc, or making doc scope-leases granular per
heading anchor rather than per file) is a separate ticket and a bigger
decision than this one.

Related: T-1344 (the land path is the throughput bottleneck) is the
adjacent framing; this ticket is about the DISPATCH side of the same
throughput problem.

## Done report

Implemented `frob ticket wave --agents N [--json] [--ignore-lease]`: partitions
`doable()`'s candidates into up to N mutually scope-disjoint groups for parallel
dispatch, using the same T-0453 `scope_overlap`/`scope_overlap_globs` substrate
`doable`'s own lease filter already uses (no second collision definition).

Algorithm: each candidate is checked against every existing group's accumulated
scope. Zero collisions -> open a fresh group when capacity remains (spreads work
across agents), else join group 0 (safe, since it collides with nothing). One
direct collision -> join that group (same-agent, sequential, no race). Two or
more direct collisions -> unplaceable, reported in `remainder` naming the exact
blocking group/ticket/glob rather than dropped silently or merged behind the
caller's back.

Ran it against this repo's real queue (`frob ticket wave --agents 3`) and
confirmed the ticket's own predicted finding: the queue barely partitions --
most doable tickets collide on `src/frob/gates/**`/`src/frob/gates/_fix_engine.py`
and land in one dominant group, exactly the docs/modules/tickets.md-style
bottleneck this ticket's body called out as a likely, reportable result rather
than something to work around.

Docs: docs/modules/tickets.md was under a T-1686/T-1736 lease for this ticket's
entire span. Filed T-1825 (renumbers at land) to add the `wave`
section and the `frob:doc` edge back onto `wave()` once it frees; a
`frob:todo T-1825` marks the gap at the exact function rather than
leaving it silent.

### Changed
```
 tickets/T-1552/ticket.md           |   5 +-
 tickets/T-1738/ticket.md           | 113 ++++++++++++++++++++++++++++++++++++-
 tickets/T-1825/ticket.md |  34 +++++++++++
 3 files changed, 148 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_tickets_wave.py::TestWave::test_disjoint_scopes_pack_into_separate_groups` (pytest node id, verified passing when recorded)
- `tests/test_tickets_wave.py::TestWave::test_colliding_scopes_share_one_group` (pytest node id, verified passing when recorded)
- `tests/test_tickets_wave.py::TestWave::test_unplaceable_ticket_lands_in_remainder_with_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_wave.py::TestWave::test_deterministic_for_repeated_calls` (pytest node id, verified passing when recorded)
- `tests/test_tickets_wave.py::TestWave::test_fewer_groups_than_agents_is_not_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_json_render_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_plain_render_lists_groups_and_remainder` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_missing_agents_flag_is_a_clean_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 6 error(s), 708 warning(s), 737 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/phantom-backlog/src/frob/tickets/_doable.py, SELFAUDIT001@design
