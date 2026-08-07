---
id: T-1542
title: fix 10 stale ticket-id citations DOC011 found, then promote DOC011 WARN to
  ERROR
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/README.md docs/audits/perf.md docs/modules/dup.md docs/modules/gates.md
  docs/modules/serve.md docs/modules/strata.md docs/modules/tickets.md docs/strata/host.md
  src/frob/gates/_doclink_docanchor.py
- tests/unit/gates/test_doc011.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_doc011.py
  reason: BUG002 needs a real fail-then-pass test proving the WARN->ERROR severity
    promotion, not just pre-existing rule-firing tests
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_unknown_ticket_id_fires_at_error_severity
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_known_active_ticket_id_passes
designated_repro_test: null
threat: null
component: null
---
T-1486 shipped DOC011 (a T-####/T-draft-<hex> mention in doc prose that
does not resolve to any active or archived ticket) as a WARN-severity
gate rather than ERROR, specifically because its first live run against
this repo's own docs tree found 10 genuine pre-existing stale citations,
entirely outside T-1486's own declared scope to fix:

  docs/audits/README.md:31        T-draft-0b60dd31
  docs/audits/perf.md:159         T-draft-bafbce1c
  docs/modules/dup.md:615         T-draft-d6bca168
  docs/modules/gates.md:1175      T-0104
  docs/modules/gates.md:1177      T-draft-4e98abb1
  docs/modules/gates.md:1178      T-draft-05d8f716
  docs/modules/serve.md:726       T-draft-8a56400c
  docs/modules/strata.md:254      T-9999 (may be an intentional example)
  docs/modules/tickets.md:2235    T-draft-2f611252
  docs/strata/host.md:542         T-draft-7b5b5541

Most are T-draft-<hex> ids that finalized to a real T-#### long ago --
fix each by resolving what the draft became (git log/tickets-archive.md
should show the renumber) and updating the citation, or confirm T-9999
is deliberately illustrative and leave it (maybe reword to make that
obvious, e.g. T-####). T-0104 needs its own check: either a genuine typo
for a real id, or a citation that should be dropped.

Once this list is provably empty (re-run `frob check --only docstatus`
unscoped), promote DOC011's severity from WARN to ERROR in
src/frob/gates/_doclink_docanchor.py::_doc011_violation -- this ticket
was only ever meant as a soft landing, not the permanent posture.