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
- mode: set
  reason: remove the body waive that measurement showed does not suppress a frontmatter
    finding; record the measurement instead and fix the gate
  actor: logan
  at: '2026-09-05'
  old_length: 987
  new_length: 890
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI NOTE, 2026-09-05. This ticket's TITLE names the config section it proposes
to create, and DOC006 flags it as a non-resolving config reference pointer at
tickets/T-3807/ticket.md:4. That single finding was the ONLY failure on the
ubuntu and macOS CI legs, via
tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo
::test_doc004_doc006_zero_against_live_repo, which asserts DOC004/DOC006 are
zero against the live repo.

A body-level `frob:waive DOC006` was tried and MEASURED NOT TO WORK: the finding
is in YAML frontmatter, and the waive mechanism DOC006's own message points at
is an inline HTML comment adjacent to the citation, which cannot exist inside
YAML. The finding is unwaivable by construction from this file.

The cause is being fixed in the gate rather than papered over here -- see the
DOC006 frontmatter ticket. Nothing in this ticket's own scope needs to change.
