## Done report

T-1825 closes T-1738's disclosed doc gap: docs/modules/tickets.md's
public-api section gained a `wave` subsection next to `doable`
describing the partition algorithm (union-scope disjointness across
groups, intra-group collision is fine since one agent works a group in
order, remainder semantics naming the exact blocking group/ticket/glob).
wave()'s own frob:doc edge is restored, and WaveGroup/WaveResult/
WaveRemainderReason each gained one too.

Per coordinator direction, also fixed the three ARCH findings the same
T-1738 land left as debris (main was red at 7 errors total: 4 COV001 +
3 ARCH, this ticket's own plan covered only the COV001 half):
- wave() (98 vs 60 lines): split its per-candidate packing step into
  _place_wave_candidate.
- _query.py::_wave (72 lines, plus ARCH103 mixing I/O, string-
  formatting, and 10 decision points): split into _render_wave_json/
  _render_wave_plain.

frob check --ticket T-1825: 0 errors in wave/_doable.py/_query.py's own
diff (the remaining COV001/E501/TEST001 findings in
src/frob/registry/_staleness.py are unrelated, landed on main by a
sibling agent between checks).
frob check --land-parity: 0 unscoped errors attributable to this
ticket's own diff (same unrelated _staleness.py residue).

### Changed
```
 docs/modules/tickets.md              |  92 +++++++++++++
 rapid-debt.jsonl                     | 258 +++++++++++++++++++++++++++++++++++
 src/frob/app/ticket_runner/_query.py |  52 ++++---
 src/frob/tickets/_doable.py          | 116 +++++++++-------
 tickets/T-1686/done-report.md        |  70 ++++++++++
 tickets/T-1686/ticket.md             |  47 +++++++
 tickets/T-1825/ticket.md             |  43 +++++-
 tickets/T-1835/ticket.md   |  27 ++++
 8 files changed, 638 insertions(+), 67 deletions(-)
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
- gates: 3 error(s), 1085 warning(s), 739 waived
- error-findings: COV001@src/frob/registry/_staleness.py, E501@/home/logan/projects/frob/.claude/worktrees/verify-cluster/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py
