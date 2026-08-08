---
id: T-1851
title: Wire --reason/--reason-file into frob ticket evidence --designate-repro (T-1749
  CLI follow-up)
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1749: `set_designated_repro_test`
(src/frob/tickets/_setters.py) now accepts an optional `reason` kwarg and
records a `DesignatedReproChangeEntry` audit-trail entry
(src/frob/tickets/_models.py) whenever a REDESIGNATION happens (an
already-set `designated_repro_test` changing to a different bound id).
`reason` is currently always `None` in practice because nothing wires it
through the CLI: `frob ticket evidence <id> --designate-repro NODE-ID`
(src/frob/app/ticket_runner/_verify.py's `_evidence_apply_designate_repro`)
has no `--reason`/`--reason-file` flag, and `AppConfig`
(src/frob/app/config.py) has no field to carry it.

This ticket is the CLI wiring: add `--reason TEXT`/`--reason-file PATH`
to the `ticket evidence` argparse group
(src/frob/_cli_parsers/_ticket/_closeout.py, wherever `--designate-repro`
itself is registered), thread it through `AppConfig`
(src/frob/app/config.py), and pass it to `set_designated_repro_test` from
`_evidence_apply_designate_repro`. Once wired, decide whether to make
`reason` REQUIRED on redesignation specifically (mirroring
`replace_evidence`'s `EvidenceReplaceReasonMissing` refusal, T-1733's own
precedent) -- T-1749's own body suggested this but a CLI-level required-
reason enforcement needs the flag to exist first.

Out of T-1749's own scope: CLI parser changes
(src/frob/_cli_parsers/**) and src/frob/app/config.py were both
explicitly off-limits to the agent that did T-1749's work.
