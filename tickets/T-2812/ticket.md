---
id: T-2812
title: 'REG008 burn-down batch 1/N: 19 missing frob:enforces directives in gates/perf
  modules'
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2369
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_root_asset_dirs.py
- src/frob/gates/_env_var_docs.py
- src/frob/gates/_lexical_selfcheck.py
- src/frob/gates/_port_selfcheck.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/__init__.py
- src/frob/gates/_milestone.py
- src/frob/perf/_dup_spawn.py
- src/frob/gates/_policy_weakening_gate.py
- src/frob/gates/_rule_id_scan.py
- src/frob/gates/_mutation_evidence.py
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_docblocks.py
  reason: T-2359 holds a live lease on this file; excluded per fleet-status LEASES
    check, per coordinator instruction to exclude live files
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 1/N of T-2369 (Burn REF001/REF002 + REG008 WARN gates to zero, then
promote to error). Batched per the T-2359/T-2373/T-2370 precedent: real
narrow scope per batch, landed independently, parent stays open until
every batch lands, severity promotion (WARN -> error) deferred to the
LAST batch.

Measured via one reused unbudgeted `frob check --json`
(docs/investigations/T-2796-backlog-reproduction.md's check run,
2026-08-21), filtered to severity=warning. Live count at the time of this
ticket: REF001 = 257 warnings, REF002 = 6 warnings, REG008 = 36 warnings
(2 files: docs/design/registry/check-coverage.yaml,
docs/design/registry/arch-checks.yaml).

This batch: REG008 only (the smallest, most mechanical of the three --
REF001/REF002 are left for a later batch, not attempted here). REG008
fires when a registry disposition entry names `handled_by:<RULE>` but no
`# frob:enforces <ENTRY-ID>` directive exists anywhere in code pointing
back at it -- the registry's own claim of enforcement is undeclared in
the code that allegedly provides it.

Fixed 19 of 36 entries by adding the missing `# frob:enforces <ENTRY-ID>`
directive directly above each rule's actual violation-emitting function
in src/frob/gates/*.py and src/frob/perf/_dup_spawn.py (12 files, verified
individually: located each rule's real `rule="<RULE>"` (or the module's
existing `# frob:enforces CHK-GATE-<RULE>` sibling directive) construction
site, confirmed the enclosing function, and added the additional entry-id
directive matching the established per-function pattern, e.g.
`_cov006`'s `# frob:enforces CHK-GATE-COV006`). Verified via a fresh
`frob check --only registry --json`: REG008 warning count dropped
36 -> 17, and the 19 entries fixed here (ROOT001, ENV001, DOC012,
LEXCHECK001, PORT001-IDENT, PORT001-PATH, PORT001, DOC013,
CHK-THEME-GITIGNORED-TRUST (TEST006's second disposition), MILE001,
MILE002, MILE003, MILE004, PERF012, INV051, GATERULE001, TEST018 (a
second disposition entry alongside mutation_evidence_violations'
existing CHK-GATE-TEST016 enforces), BUG003, SYS111) are all confirmed
gone from the live REG008 output.

Remaining 17 entries (not this ticket's scope): SLH-SYS-EVA-03-UNDECLARED
-PUBLIC-SURFACE, SYS108, SYS109, SYS110, SYS112, BUDGET001, CHECK001,
CVEFP001, DEPLOY001/002/003, DERIVED001, CAP001, CLAUDE001, EXHAUST004,
CYCLE001, QUEUE001 -- these are implemented via `Diagnostic(code=...)`
in app/check_runner.py, deploy/_conform.py, check/__init__.py,
check/_python.py, strata/_selfconform.py, app/_check_chunking.py rather
than the gates/*.py `Violation(rule=...)` convention this batch used, and
several are outside the `frob.gates` package's established
`frob:enforces` placement pattern entirely -- each needs its own
verification of where a directive belongs before it is safe to add, left
for the next batch. REF001 (257) and REF002 (6) are untouched.
