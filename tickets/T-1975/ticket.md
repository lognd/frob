---
id: T-1975
title: Wire frob ticket scope --demote-to-evidence-only to T-1944's demote_to_evidence_only
state: in-progress
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/_mutate.py
- tests/test_tickets_scope_mutation.py
- src/frob/app/_config_external.py
- tickets/T-draft-1461df22/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: the CLI runner-side wiring (parsing cfg.ticket_scope_demote_to_evidence_only
    and calling demote_to_evidence_only) lives in _mutate.py, matching --add/--remove's
    own existing wiring in the same function; test coverage lives in the existing
    scope-mutation CLI test module
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: the CLI runner-side wiring (parsing cfg.ticket_scope_demote_to_evidence_only
    and calling demote_to_evidence_only) lives in _mutate.py, matching --add/--remove's
    own existing wiring in the same function; test coverage lives in the existing
    scope-mutation CLI test module
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/_config_external.py
  reason: WIRE001 requires the new CLI dest registered in _config_external.py's field-name
    tuple (T-1422's shape), matching --add/--remove's own registration; the draft
    ticket file is residue filed earlier this session, riding along in this land
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-draft-1461df22/ticket.md
  reason: WIRE001 requires the new CLI dest registered in _config_external.py's field-name
    tuple (T-1422's shape), matching --add/--remove's own registration; the draft
    ticket file is residue filed earlier this session, riding along in this land
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_demote_to_evidence_only_releases_lease
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_demote_to_evidence_only_requires_declared_glob
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Follow-up from T-1944 (evidence-only scope): `frob.tickets.demote_to_
evidence_only` exists and is tested, but there is no CLI surface for it
yet -- an operator/agent unblocking a T-1686-shaped stuck ticket today
has to call the library function directly rather than run a `frob
ticket scope` subcommand. Wire `frob ticket scope <id> --demote-to-
evidence-only GLOB... --reason TEXT` (or a dedicated verb, whichever
matches this repo's existing `scope`/`scope-ack` CLI convention more
closely) through `src/frob/_cli_parsers/_ticket/`.

Left out of T-1944's own scope (declared `src/frob/tickets/`) because
the CLI parser tree lives outside that path.
