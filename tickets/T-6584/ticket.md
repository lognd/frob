---
id: T-6584
title: sys audit exhaustiveness pass reports ticket-bound SYS114/SYS115 waivers as
  stale SYSWAIVE002 because _gap_rule_in_scope does not exclude the outbound-destination
  channel
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/strata/_audit.py
- src/frob/strata/_outbound_destination.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the project-hullbreach session (2026-09-26) on
/home/logan/projects/project-hullbreach/game/design/hullbreach_game.strata
with two ticket-bound `waive "SYS114:f_login_game" ...` lines (the idiom
docs/strata/threat.md documents). The reliability view reports "SYS114 0
violations, 2 waived, 0 stale" (check_outbound_destination applies them,
T-4113), but `frob sys audit`'s exhaustiveness pass applies every node's
waive clause against the family-gap set too, and since it never generates
SYS114 gaps those same waivers match nothing there and become stale
SYSWAIVE002 gaps; the audit exits non-zero. Verified on dev b41443f46d:
`_gap_rule_in_scope` (src/frob/strata/_audit.py) excludes SYS100-102,
SYS205, HOST001/002, SYS200-203 and the REL rules, but not SYS114/SYS115
(`SYS_UNCONSTRAINED_DESTINATION` and its sibling), which own their own
waiver channel in _outbound_destination.py. The platform repo shows the
same pattern.

Deliver: add the outbound-destination rule ids to the exclusion so a rule
with its own channel is never double-owned; positive control: a fixture
model with one SYS114 waiver that matches a real finding; the audit
reports it waived once and no SYSWAIVE002. Audit the other self-channel
families (SEC110, KRB, DEPLOY) for the same gap while there.
