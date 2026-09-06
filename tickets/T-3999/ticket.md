---
id: T-3999
title: 'F-213: close resolves a pytest verdict for rust-only evidence, emitting BUG002
  NotImportable about a question it could not ask'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-213, 2026-09-06:

  "Both evidence ids on T-0181 are wasm-engine/src/*.rs::tests::* node ids;
   close still tried to resolve a pytest verdict for them and emitted BUG002
   NotImportable. Harmless (close still succeeded) but noisy -- the verdict
   resolver should route by evidence-id file extension/language before reaching
   for a Python interpreter."

They call it harmless, and for their run it was. IT IS NOT HARMLESS AS A CLASS,
which is why it is worth a ticket rather than a shrug.

A gate that reaches for a Python interpreter to resolve a RUST test id is
producing a NotImportable verdict about a question it was never able to ask. If
that verdict is ever consumed as a signal rather than printed as noise, the
result is an infrastructure failure being read as a semantic one -- the exact
class this repo has now catalogued five times (a killed child read as
"unmeasurable", a collection exit-2 read as "evidence gone", a malformed ledger
read as "ticket not found", a merge conflict read as "evidence did not pass").
Here the wrong answer happened to be discarded. The next caller may not discard
it.

IT ALSO TRAINS THE WRONG HABIT. A close that routinely prints a scary-looking
"pytest is NOT importable" while succeeding teaches users that close warnings are
noise. That is expensive the first time a real one appears.

THIS IS THE PYTHON-DEFAULT ASSUMPTION AGAIN, and it now has a pattern. Related,
all confirmed, all the same root shape -- a code path assuming python until
proven otherwise:
  - T-3945: normalize_evidence_separator mangles dotted kotlin ids.
  - T-3981: an unresolved rust id is told "this test does not exist in this
    tree" when it exists one module segment away.
  - T-3937/T-3925: the binding path resolved only python and rust for a long
    time; ts/cpp/kotlin ids were rejected outright.
Whoever takes this should look at the group rather than patching one call site.
LANGUAGE_COLLECTORS already exists as the one registry keyed by the same
language name a test.runner entry uses; the verdict resolver should route
through that registry rather than defaulting to python and discovering the
mismatch by exception.

WHAT TO DETERMINE FIRST: is routing by FILE EXTENSION (the consumer's suggestion)
right, or should it route by the language of the matching test.runner? Extension
is simpler but wrong for a repo where one extension is served by two runners, and
right-looking until then. Prefer the registry the evidence was collected through,
falling back to extension only if no runner claims the id -- and say which you
chose and why.

MUST-FIRE FIXTURE: a ticket with ONLY rust evidence closes with no python
interpreter consulted and no NotImportable emitted.
MUST-STAY-QUIET: a ticket with python evidence still gets a real pytest verdict.
THIRD FIXTURE: a ticket with MIXED python and rust evidence resolves each id
through its own language, with neither leaking into the other's verdict.

ACCEPTANCE
- Verdict resolution routes by the collecting runner/registry, not by a python
  default; the extension-vs-runner decision stated.
- No interpreter is consulted for a language it cannot answer for.
- All three fixtures committed.