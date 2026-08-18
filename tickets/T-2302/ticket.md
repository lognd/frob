---
id: T-2302
title: 'T-2123 follow-up: no filing-time scope-breadth acknowledgement path, so the
  new-ticket breadth check is advisory forever'
state: done
kind: feature
origin: agent
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_new.py
- src/frob/tickets/_models.py
- src/frob/tickets/_new_renumber.py
- docs/modules/tickets-data-storage.md
- tests/unit/test_new_ticket_scope_breadth_ack_flag.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/config.py
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/_config_external.py
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_models.py
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: wiring --scope-breadth-ack CLI flag through TicketSpec/AppConfig, T-2302
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_new_ticket_scope_breadth_ack_flag.py
  reason: must-fail fixture for --scope-breadth-ack flag
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_acknowledged_broad_scope_is_silent_and_recorded
- tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_unacknowledged_broad_scope_still_warns
- tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_ack_without_reason_is_refused
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: given a deliberately broad scope at filing time, when the operator passes
    the acknowledgement flag, then the scope is recorded as acknowledged rather than
    merely warned about
  evidence:
  - tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_acknowledged_broad_scope_is_silent_and_recorded
  - tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_unacknowledged_broad_scope_still_warns
  - tests/unit/test_new_ticket_scope_breadth_ack_flag.py::TestScopeBreadthAckFlag::test_ack_without_reason_is_refused
- text: given the acknowledgement path exists, when the filing-time severity decision
    is made, then it is recorded with the measured count of currently-queued tickets
    that would fail a refusal
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: 744953cac6e0420c9ce7ce2e30e6ff2e0596a411
---
T-2123 (landed 2026-08-17, commit 4f38aad1) made `frob ticket new` WARN on
an unacknowledged over-broad scope at filing time, reusing the
TICK009/`large_glob_warnings`/`scope_breadth_ack` mechanism T-1866
established for start-time.

It shipped WARN-only rather than as a hard refusal for a sound reason,
disclosed in its Done report: at FILING time the ticket has no id yet, so
there is nothing for the operator to acknowledge against. The
acknowledgement path that exists at start-time (`scope_breadth_ack`) has no
filing-time equivalent.

THE GAP: that leaves the filing-time check advisory forever. An agent or
operator can file an arbitrarily broad scope, see a warning scroll past, and
proceed -- which is exactly how a single ticket ends up locking dozens of
files and serialising a whole dispatch wave. The Done report notes a
`--scope-breadth-ack` CLI flag as the follow-up and explicitly declined to
file it speculatively.

Filing it here so the follow-up is tracked rather than living only in an
archived Done report.

REQUIRED:
 - Add an explicit acknowledgement path at filing time (e.g.
   `frob ticket new --scope-breadth-ack`), so a deliberately broad scope is
   a recorded, intentional choice rather than an ignored warning.
 - Once that path exists, decide whether the filing-time check should
   escalate from WARN to a refusal-unless-acknowledged, matching the
   start-time posture. Record the decision either way.

MEASURE BEFORE CHANGING SEVERITY: count how many currently-queued tickets
would fail a refusal-unless-acknowledged check. If that count is large, the
escalation needs its own burn-down ticket first -- shipping a refusal that
reddens existing work repeats the mistake T-1783 correctly avoided by
shipping DOC012 at WARN (see T-2299).