---
id: T-3949
title: 'F-187: symbol-level scope satisfies AFFECT/COV/PRE but not SCOPE001, so whole-file
  leases still serialise disjoint edits'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: T-3927
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- src/frob/tickets/_models.py
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
Consumer logand.app-v2 F-187, plus an unnumbered 2026-09-06 report of the same
shape. This is now the FIFTH report of one problem from this consumer -- they
name F-127 and F-145 as the same theme, and it recurs across sessions and agents.
It is their single most-reported friction.

THE ASK, in their words: "Either SCOPE001 should honour symbol-level scope, or
leases should be symbol-level."

INSTANCE 1 (F-187). T-0173 needed ONE column in db/models/admin.py (leased by
T-0170) and ONE constructor argument in app/app.py (leased by T-0171).
`frob ticket scope --add admin.py::AdminAlert` WAS ACCEPTED and cleared the
closure gates -- AFFECT, COV and PRE were all satisfied by the symbol-level
scope. But SCOPE001 still demanded the literal FILE, the whole-file lease
refused it, and the ticket blocked itself on T-0170 and filed T-0177 purely to
finish later.

INSTANCE 2 (unnumbered, same day). T-0176 could not amend its OWN row in
docs/spec/L5-component-design/SUB-03-db.md: ScopeLeaseConflict, held by
in-progress T-0173. T-0173's declared scope per its dispatch brief was
notifications/app.py/models/admin.py -- not that doc at all; the lease was on a
whole-file glob whose actual edits never touched the row T-0176 needed. T-0176
shipped WITHOUT the amendment.

WHAT MAKES THIS A DESIGN DEFECT RATHER THAN FRICTION. Symbol-level scope is
ALREADY ACCEPTED and ALREADY SUFFICIENT for three of the four gates that consume
scope. SCOPE001 and the lease are the two that ignore it. So the system offers a
precision it then refuses to honour -- the user does the right thing, is told it
worked, and is blocked anyway. That is worse than not supporting symbol scope at
all, because it wastes the user's correct action.

IT ALSO CAPS PARALLELISM DIRECTLY, which is the expensive part. Two tickets with
provably disjoint edits inside one file cannot proceed concurrently. The
consumer's remedy in both instances was to serialise and file a follow-up ticket
-- so the defect manufactures queue entries.

THIS IS THE SCOPE-CONFLATION EPIC (T-3927) MEASURED IN THE FIELD. Scope is a
write lease AND an evidence-coverage declaration in one field; these two reports
are what that conflation costs. Treat this ticket as T-3927's motivating
evidence, and check T-3927 before designing -- do not re-derive the analysis.

DETERMINE FIRST, BEFORE CHOOSING A FIX: why does SCOPE001 demand the literal
file when AFFECT/COV/PRE do not? If that is deliberate (a soundness requirement
-- e.g. it cannot prove a symbol-level edge without the whole file), then the
answer is symbol-level LEASES, not symbol-level SCOPE001, and the ask resolves
the other way. If it is merely an unexamined file-granularity assumption, honour
the symbol scope. DO NOT GUESS BETWEEN THESE -- the two fixes have opposite
shapes and the consumer explicitly offered both.

THE CHEAP HALF, worth doing regardless of which fix wins: their second report
asks for "at least a way to SEE which glob T-0173 actually leased so a human can
judge overlap before it blocks." The refusal message today names the holder but
not the glob that actually collided. That is a message change, it is
independently useful, and it does not wait on the design decision.

MUST-FIRE FIXTURE: two tickets whose symbol-level scopes genuinely OVERLAP still
conflict.
MUST-STAY-QUIET: two tickets with disjoint symbol-level scopes in the SAME FILE
both proceed. This is the fixture that proves the ticket.
THIRD FIXTURE: the refusal message names the specific colliding glob.

ACCEPTANCE
- The SCOPE001 file-granularity question answered (deliberate or unexamined),
  with the reason, before any fix is chosen.
- Disjoint symbol-level edits in one file no longer serialise.
- The refusal names the colliding glob.
- All three fixtures committed.