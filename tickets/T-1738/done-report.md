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
