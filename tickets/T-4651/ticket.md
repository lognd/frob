---
id: T-4651
title: 'Kernel decoupling: ledger, leases, land, gates behind enforced boundaries'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: epic
sprint: v0.535.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic/story rollup for the kernel-decoupling epic:
  all file work lives in the leaf children; this ticket carries no write lease by
  design'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-19: frob is becoming very monolithic and coupled. This epic is a REDERIVATION of the frob kernel, NOT a rewrite. The CLI surface, the comment DSL, the tickets/<id>/ticket.md file format and the existing test suite are FROZEN as the contract; the four kernel concerns are rebuilt behind explicit module boundaries that frob check itself enforces.

Measured pain this epic must end (week of 2026-09-15..19):
- draft ids renumbered inside worktrees, and renumber races between concurrent agents
- whole-file leases on shared registry files (design/frob.strata, capability-via-ratchet.lock.json, docs/modules/gates.md, frob.toml severity zone) blocking every sibling land and scope --add
- the land taking 10-25 min to compose, then losing the CAS race to ledger-only commits
- the post-land sweep holding .frob/derived.lock READ for 30 min, blocking the next land
- frob ticket doable / new taking 5+ minutes (quadratic per-lease rescans)
- every new gate rule needing a hand edit of gates/__init__.py AND _KNOWN_GATE_RULES

Concerns (one story each):
1 LEDGER  ids assigned once at new; draft promotion is a ledger-only operation performed by land; worktrees never renumber; one typed store API module every other module goes through.
2 LEASES  explicit lifecycle (acquire on start, release on EVERY terminal transition incl. drop/fail); append-shared registry files; lease store independent of land and gates.
3 LAND    explicit logged state machine prepare -> compose -> publish -> post-publish; compose pure over a snapshot; publish a CAS with a ledger-only fast path; post-publish never rebuilds a snapshot and never holds derived.lock across a full check.
4 GATES   one registration interface from which the job list, _KNOWN_GATE_RULES, the docs/modules/gates.md enumeration and check-coverage.yaml are DERIVED -- adding a detector is one file.
5 LAYERING  [arch.layering] declaring ledger < leases < land < app with gates independent, ARCH10x red on violation, frob cycle clean on src/frob/tickets.

OUT OF SCOPE: the strata language grammar and semantics (owner is redesigning personally). strata-core and design/frob.strata edits only where a kernel boundary needs a declared flow.

Every leaf carries a POSITIVE CONTROL in its acceptance list: a test that FAILS on the old coupling, so a green suite proves the boundary, not the absence of a matcher.