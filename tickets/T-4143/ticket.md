---
id: T-4143
title: the evidence list cannot shrink through any verb, forcing agents to hand-edit
  the ledger, and its null form crashes scope edits
state: in-progress
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'F-347''s crash (evidence: null -> TypeError not iterable) is raised inside
    _models.py''s _split_scope_entries/_coerce_acceptance/Ticket.evidence field, not
    _evidence.py; the loader-boundary fix per the ticket''s own instruction must land
    where the crash actually originates'
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a stale evidence entry including a command-shaped one, when the removal
    verb is run with a reason, then the entry is dropped and the reason is recorded
  evidence: []
- text: given an evidence removal, when it completes, then the remaining entries keep
    their order and their acceptance-criterion bindings
  evidence: []
- text: given a ticket whose evidence key is YAML null, when a scope add or remove
    runs, then it succeeds and no crash occurs
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE EVIDENCE LIST HAS NO SUPPORTED WAY TO SHRINK, AND ITS EMPTY FORM CRASHES A
DIFFERENT VERB. Two logand.app-v2 reports, one underlying gap: the lifecycle of
the evidence field is specified for growth and for replacement-in-kind, and not
for anything else.

MECHANISM ONE -- NO REMOVAL VERB, SO AGENTS HAND-EDIT THE LEDGER (F-345).
There is no way to drop a stale evidence entry. The replace path only swaps
pytest node ids and refuses command-shaped targets outright. Their agent, needing
to drop empty-digest command evidence after appending the real replacement, HAND
EDITED SEVEN TICKET FILES.

THAT IS THE PART THAT MAKES THIS URGENT RATHER THAN A CONVENIENCE REQUEST. This
repo has a recorded incident where a hand edit to the ledger -- a single stray
character in prose -- broke the ledger's YAML and took EVERY GATE DOWN
repo-wide. The standing rule since then is to use the frob verbs and never hand
edit. Here the tool leaves no verb that does the job, so the rule and the task
are in direct conflict and the agent must break one of them. That is a no-exit
whose only exits are the two things we most want to avoid: corrupt the ledger by
hand, or leave known-false evidence attached to a ticket.

Their proposed fix is right on both halves: add an explicit removal that takes an
entry or index with a required reason, and let the replace path accept
command-shaped entries rather than refusing them.

MECHANISM TWO -- A NULL EVIDENCE FIELD CRASHES SCOPE EDITS (F-347).
A ticket whose evidence key is YAML null rather than an empty list crashes the
scope add/remove verb with "'NoneType' object is not iterable". A crash, not a
refusal. The loader should normalise null to the empty list, or refuse with a
message that names the file and the field.

These two belong together because they are the same omission seen twice: nothing
owns the evidence field's empty and shrinking states. Note also the likely causal
link -- an agent forced to hand-edit evidence out of a ticket (mechanism one) is
exactly how a field ends up as null instead of an empty list (mechanism two).
Fixing only the crash would leave the process that produces it intact.

WHAT TO DO
  1. Normalise at the loader. A null evidence key becomes the empty list at the
     boundary, so no downstream caller has to defend against it. Do this first;
     it is small and it stops a crash.
  2. Add the removal verb, with a required reason recorded the way other
     destructive ledger verbs record one.
  3. Let replacement accept command-shaped entries. Find out WHY it refuses them
     before removing the refusal -- if the refusal exists to prevent something
     real, the fix is to handle that case, not to delete the guard.
  4. Audit the other ledger list fields for the same null-versus-empty
     asymmetry. Evidence is unlikely to be the only one, and the crash shape will
     be identical wherever it exists. Report the list.

MUST-FIRE FIXTURE:   a stale evidence entry, including a command-shaped one, can
                     be removed through a verb, with the reason recorded.
MUST-STAY-QUIET:     removing an entry does not disturb the remaining entries'
                     order or their acceptance-criterion bindings.
THIRD FIXTURE:       a ticket whose evidence key is null loads as an empty list
                     and every scope edit succeeds, with no crash anywhere.

ACCEPTANCE
- Null normalised at the loader, not defended against per-caller.
- A removal verb exists and records a reason.
- Replacement accepts command-shaped entries, with the reason its refusal existed
  either preserved differently or explained as obsolete.
- Other ledger list fields audited for the same null-versus-empty asymmetry.
- All three fixtures committed.
