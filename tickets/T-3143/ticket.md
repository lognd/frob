---
id: T-3143
title: refactor split leaves type-annotation-only import sites unrepointed
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/refactor/_scan.py
  reason: reference-collection pass this ticket investigates/widens
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED during T-3086 (frob refactor split frob.gates._models --symbols
Severity,WaiverRef,DebtEntry,Violation --into frob.findings): the split
applied cleanly, both modules import correctly, and all three verify
post-conditions passed. But of ~28 non-gates source files that import one
of the four moved value types from frob.gates._models, only 3
(src/frob/vet/_models.py, src/frob/app/vet_runner.py,
src/frob/tickets/_land.py) were repointed to `from frob.findings import
...` directly. The other ~25 (src/frob/dup/_rules.py, fuzz/_rules.py,
perf/_advisories.py and siblings, policy/__init__.py, vet/_ecosystem.py,
vet/_scan.py, etc.) still read `from frob.gates._models import Severity,
Violation` (or similar) unchanged.

This is NOT a correctness bug -- gates/_models.py re-exports the moved
names (the same T-1201 backward-compat pattern already used elsewhere in
that file), so every one of those imports still resolves and every test
still passes. It IS an incompleteness relative to what a full "these
importers now import the leaf" migration would look like.

SUSPECTED ROOT CAUSE (not confirmed -- worth verifying first): the files
that DID get repointed have a `from frob.gates._models import Violation`
line whose ONLY name is a moved symbol used in a real expression context
(a function call or attribute access). The files that did NOT get
repointed appear to use the moved names only as TYPE ANNOTATIONS (e.g.
`def f(v: Violation) -> str:`), which src/frob/refactor/_scan.py's
reference-collection pass may not be counting as call sites at all.

Verify this hypothesis against src/frob/refactor/_scan.py's reference
collection, then widen it to catch type-annotation-only usages of a moved
symbol so a future split's reference-rewrite actually reaches every real
consumer, not just the ones using the symbol in an expression position.
