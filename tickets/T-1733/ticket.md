---
id: T-1733
title: Weakening a ticket's evidence is silent and free, while the honest escape hatch
  is logged and justified
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/gates/_mutation_evidence.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/gates.md
- src/frob/tickets/_models.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_mutate.py
- tests/test_tickets_evidence_cli.py
- tests/test_tickets_mutation_evidence.py
- src/frob/tickets/_mutation_evidence.py
- src/frob/gates/_waive.py
- tests/test_gates_mutation_evidence.py
- src/frob/tickets/_reporting.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_query.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_evidence_cli.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_mutation_evidence.py
  reason: 'T-1733 requires a new append-only audit trail for evidence weakening

    (mirroring ScopeChangeEntry/AcceptanceAmendmentEntry''s T-0455/T-1422

    precedent), which means a new Ticket model field and entry type in

    src/frob/tickets/_models.py, and a new required --reason/--reason-file

    CLI flag pair on `frob ticket evidence --replace`, which needs new

    AppConfig fields in src/frob/app/config.py (mirroring

    ticket_scope_reason/ticket_scope_reason_file). Neither file is in the

    ticket''s literal scope but both are structurally required to implement

    requirement 1 (reason required + recorded) the same way T-0455/T-1422

    did it, rather than inventing a parallel, inconsistent mechanism that

    avoids touching them.

    '
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_mutation_evidence.py
  reason: requirement 3 (refuse outright when evidence unbound AND surviving evidence
    confirmatory-only per TEST016) needs to read ConfirmatoryFinding/unmeasured from
    this module, the real engine T-1727 already established is the right home for
    mutation-evidence logic
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_waive.py
  reason: TEST018 (the new outright-refuse rule for requirement 3) must be registered
    in _KNOWN_GATE_RULES (src/frob/gates/_waive.py) per the T-0756 new-gate-rule-acceptance
    policy the ticket itself invoked ('register a real id; do not invent an unregistered
    one') -- that registry lives in this file, not gates/__init__.py, per T-1139's
    move
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: evidence_weakened/TEST018 test coverage for requirement 3 belongs in the
    existing TestMutationEvidenceViolations class in this file, matching TEST016's
    own test-file home
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/tickets/_reporting.py
  reason: requirement 4 (frob ticket show surfaces evidence churn) needs to render
    the new evidence_changes audit trail, mirroring _render_acceptance_amendments_block's
    existing T-1422 precedent in this exact file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/_config_external.py
  reason: AppConfig.from_external's field-copy tuples (src/frob/app/_config_external.py)
    must include the two new ticket_evidence_replace_reason[_file] fields or the new
    --reason/--reason-file CLI flags silently no-op (never reach AppConfig) -- same
    file T-0749's own comment in config.py describes hitting this exact gap for --accepts
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: requirement 4's real home is frob.app.ticket_runner._query._show, which
    already renders acceptance_amendments via _render_acceptance_amendments (T-1422)
    -- evidence_changes needs the identical rendering precedent applied here, not
    in _reporting.py's Done-report composer which is a different, narrower surface
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 flagged the new EvidenceChangeEntry symbol as undeclared in
    the tickets_ledger store's interface= list -- same self-audit obligation T-1727
    already hit for its own new symbols in this file
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_blank_reason_is_a_hard_refusal
- tests/test_tickets_evidence_cli.py::TestReplaceEvidenceCli::test_cli_replace_without_reason_exits_nonzero_and_writes_nothing
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_replaces_flat_evidence_and_acceptance_binding_atomically
- tests/test_tickets_evidence_cli.py::TestReplaceEvidence::test_same_old_and_new_is_a_no_op_success
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_evidence_weakened_and_confirmatory_refuses_outright
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_no_evidence_changes_never_produces_test018
- tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations::test_evidence_changes_with_strong_surviving_evidence_no_test018
- tests/test_tickets_evidence_cli.py::TestEvidenceChangesSurfaced::test_show_renders_evidence_change_and_reason
designated_repro_test: null
threat: null
component: null
---
T-1727 records that the close-time mutation sweep's cost pushes agents
toward binding cheap evidence, but every one of its requirements is about
BUDGET -- make the sweep bounded, warn earlier, report progress. All of
those make `close` faster. None of them stops a ticket closing on weaker
evidence than it started with. The insight was written down and then not
acted on, which is the catalogued-but-not-enforced shape this repo has
been burned by before.

This ticket is the enforcement half.

THE ASYMMETRY, EXACTLY. Two ways exist to get a slow close to finish:

- `--skip-mutation-evidence`: DISCLOSED. Logs loudly, demands a
  justification, lands in the Done report. The honest exit is expensive
  and permanently visible.
- Unbind the slow tests with `frob ticket evidence --replace`: SILENT.
  Requires no reason, records nothing, leaves no trace anyone reviews.

So the tool bills the honest exit and comps the quiet one. Observed
live on 2026-08-07: an agent facing ten consecutive 540s close timeouts
unbound its three `TestSpawnWithWatchdog` tests -- the only evidence that
actually exercised the subprocess watchdog the ticket existed to build --
and the ledger shows nothing about it. It surfaced only because the agent
volunteered it in prose.

The precedent for the fix is already in this CLI and one verb away:
`frob ticket scope` REQUIRES `--reason` (or `--reason-file`) for any
scope change, and records it. Narrowing what a ticket covers is treated
as a decision worth writing down. Narrowing what PROVES it is not. There
is no principle that makes scope worth recording and evidence not.

REQUIRED:

1. Any evidence REMOVAL or replacement requires `--reason`, recorded in
   the ticket, exactly as `frob ticket scope` already does. Pure additions
   stay free -- the point is to price weakening, never to tax
   strengthening.
2. A gate rule (register a real id; do not invent an unregistered one)
   that refuses a close when the bound evidence set SHRANK during the
   ticket's life without a recorded reason. Shrink means fewer ids, or
   the same count with a strong id swapped for a weaker one.
3. The specific pattern to refuse OUTRIGHT, not merely flag: evidence was
   unbound AND the surviving evidence is confirmatory-only per TEST016.
   That is the exact fingerprint of "the tests that proved it were
   removed so it would close", and it is mechanically detectable because
   TEST016 already computes the confirmatory-only verdict.
4. `frob ticket show` surfaces evidence churn -- what was bound, what was
   unbound, and why -- so a reviewer sees the history rather than the
   final list. A final list that looks fine is precisely what an unbind
   produces.

THE PRINCIPLE WORTH STATING IN THE DOCS, because it generalises past this
ticket: EVERY WAY TO MAKE A TICKET EASIER TO CLOSE MUST COST AT LEAST AS
MUCH BOOKKEEPING AS THE HONEST WAY. Wherever a cheap exit is quieter than
the expensive one, the cheap exit is what will be taken, and the ledger
will look clean while the evidence rots. Audit the other verbs against
that rule while implementing this one, and report any others found --
`--skip-mutation-evidence` versus silent unbinding is unlikely to be the
only pair.

Do NOT make this a warning. A warning here is advice about an action
already taken, at the moment the caller is most motivated to ignore it.

Sibling: T-1727 (the cost that creates the pressure). Fixing that reduces
the motive; this removes the means. Both are needed -- a bounded sweep
still leaves unbinding free, and pricing unbinding still leaves an agent
staring at a 90-minute close.