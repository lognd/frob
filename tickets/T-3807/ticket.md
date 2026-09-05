---
id: T-3807
title: 'F-007: frob check cannot see a polyglot monorepo whose stacks live in subdirs
  (CHECK001 unknown project type) -- let frob.toml declare [[check.stack]] type/cwd,
  reusing the [[test.runner]] cwd'
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: waive the title-line DOC006 that is the sole ubuntu and macOS CI failure;
    the pointer is future-facing by construction
  actor: logan
  at: '2026-09-05'
  old_length: 0
  new_length: 987
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

CI NOTE, 2026-09-05. This ticket's TITLE names the config section it proposes
to create, and DOC006 flags that as a non-resolving config reference pointer at
tickets/T-3807/ticket.md:4. That single finding is currently the ONLY failure on
the ubuntu and macOS CI legs, via
tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo
::test_doc004_doc006_zero_against_live_repo, which asserts DOC004/DOC006 are
zero against the live repo.

The reference is future-facing by construction: the whole point of this ticket
is that the section does not exist yet.

<!-- frob:waive DOC006 reason="this ticket PROPOSES the config section its title names, so the pointer is future-facing by construction and cannot be made to resolve without implementing the feature; DOC006's own message names external/illustrative/future-facing as the exempt case" -->
The proposed section is the double-bracketed check.stack array-of-tables in
frob.toml, carrying type/cwd and reusing the test.runner cwd.
