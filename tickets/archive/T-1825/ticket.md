---
id: T-1825
title: Document frob ticket wave in docs/modules/tickets.md once the lease frees
state: done
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- src/frob/tickets/_doable.py
- src/frob/app/ticket_runner/_query.py
- tickets/T-1825/ticket.md
- tickets/T-1825/done-report.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: 'coordinator directed: T-1738''s same land left ARCH001/ARCH103 debris in
    _query.py alongside the COV001 gap this ticket''s own plan covers; fixing both
    in one pass rather than filing a third ticket'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1825/ticket.md
  reason: 'coordinator directed: T-1738''s same land left ARCH001/ARCH103 debris in
    _query.py alongside the COV001 gap this ticket''s own plan covers; fixing both
    in one pass rather than filing a third ticket'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1825/done-report.md
  reason: 'coordinator directed: T-1738''s same land left ARCH001/ARCH103 debris in
    _query.py alongside the COV001 gap this ticket''s own plan covers; fixing both
    in one pass rather than filing a third ticket'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'SCOPE002: T-1825''s scope includes a docs/modules/tickets.md anchor that
    design/frob.strata::frob.verify also describes; closing the scope-closure gap'
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
## Description

T-1738 (`frob ticket wave --agents N`) landed the code (src/frob/tickets/_doable.py's `wave`/`WaveGroup`/`WaveResult`/`WaveRemainderReason`, CLI wiring in `_cli_parsers/_ticket/_query.py` and `app/ticket_runner/{_query.py,__init__.py}`) without a docs/modules/tickets.md#public-api section, because that page was under a T-1686/T-1736 lease for the whole span T-1738 was worked.

## Plan

Once docs/modules/tickets.md frees: add a `wave` subsection next to `doable`/`doable_blocked` describing the partition algorithm (union-scope disjointness across groups, intra-group collision is fine, remainder semantics), then add the `frob:doc docs/modules/tickets.md#public-api` directive back onto `wave()` in src/frob/tickets/_doable.py.

## Acceptance

- [ ] docs/modules/tickets.md has a `wave` section under public-api
- [ ] `wave()` carries a `frob:doc` edge to it
- [ ] `frob check` reports no doc-coverage finding for `wave`/`WaveGroup`/`WaveResult`/`WaveRemainderReason`