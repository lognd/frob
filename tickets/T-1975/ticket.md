---
id: T-1975
title: Wire frob ticket scope --demote-to-evidence-only to T-1944's demote_to_evidence_only
state: done
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
- tickets/T-2009/ticket.md
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
  glob: tickets/T-2009/ticket.md
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
land_commit: null
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

## Done report

Wired frob ticket scope --demote-to-evidence-only GLOB... to T-1944's demote_to_evidence_only: new CLI flag in _add_ticket_scope_parser (_metadata.py), new AppConfig field, runner-side dispatch in _mutate.py (_apply_demote_to_evidence_only, split out from _scope for ARCH001), and registered in _config_external.py's _LIST_FIELDS (WIRE001's own requirement -- confirmed the field would otherwise be silently dropped by AppConfig.from_external before AppConfig(**d), T-1422's shape). Combinable with --add/--remove in the same call: demote runs first, then add/remove if also given. Proof of CLI wiring (not just the already-tested library function): test_cli_demote_to_evidence_only_releases_lease drives the real _scope entrypoint end to end and asserts the glob actually moved from scope to evidence_scope; test_cli_demote_to_evidence_only_requires_declared_glob proves an undeclared glob still refuses through the CLI path, matching demote_to_evidence_only's own ScopeRemoveNotDeclared guard.

### Changed
```
 tickets/T-1975/ticket.md           | 40 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2009/ticket.md | 21 ++++++++++++++++++++
 2 files changed, 60 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_demote_to_evidence_only_releases_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_demote_to_evidence_only_requires_declared_glob` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/ticket-workflow/tests/unit/test_tickets_evidence_only_scope.py, invalid-argument-type@src/frob/app/ticket_runner/_mutate.py
