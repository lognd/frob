---
id: T-4082
title: the secrets hook blocks writing the text import.meta.env into a ticket, pushing
  an agent into filing with no acceptance criteria
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
- scripts/fleet_status.py
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
THE .env SECRET-PROTECTION HOOK BLOCKS WRITING THE TEXT `import.meta.env` INTO A
TICKET. Measured today: a planner agent filing a ticket about frontend build-time
config could not pass an `--acceptance` string containing `import.meta.env` /
`process.env`, and worked around it by filing the ticket WITHOUT acceptance
criteria and adding the detail in the body instead.

NOTHING SECRET WAS INVOLVED. The blocked text was the NAME OF AN API SURFACE --
`import.meta.env` is Vite's standard build-time environment accessor, and the
ticket's subject was that an unguarded `??` default on such a read is a defect.
The hook matched on substring shape, not on anything resembling a credential.

THIS IS THE LEXICAL-HOOK CLASS, TENTH INSTANCE. The queue already tracks:
hand-rename-sed (x3), ack line-anchoring (T-3851), the root-write guard's `>=`
(T-3421), handrolled floor count, retry re-block (F-078), protect-secrets
matching its own text (T-3924), and the ticket-id regex with no left boundary
(T-4015). Every one is a guard comparing TEXT where it should compare STRUCTURE.

WHY THIS INSTANCE IS WORSE THAN MOST, and the reason it deserves a ticket rather
than a shrug: the hook's job is to prevent SECRET MATERIAL reaching a file. It
fired on a discussion OF the env mechanism, which is exactly the conversation you
must be able to have while writing security tickets. So the guard makes it harder
to DOCUMENT env-var handling defects -- the class of work most likely to prevent
a real leak. That is the protect-secrets self-reference problem (T-3924) in a new
form: the rule impedes discussing the thing it protects.

THE WORKAROUND IS ITSELF A SIGNAL. The agent filed the ticket with NO acceptance
criteria to get past the hook. Acceptance criteria are load-bearing -- T-4031 is
open specifically because tickets landing with zero criteria pass the acceptance
check vacuously. So a secrets hook, firing on a false positive, pushed an agent
into exactly the state another ticket exists to prevent. Guards that force
workarounds produce defects elsewhere.

WHAT TO DETERMINE FIRST: what does the hook actually match on? If it is a
substring list containing `.env`, then `import.meta.env` matches by accident of
containing that sequence -- a token-boundary problem with a mechanical fix. If it
matches something broader, the fix is different. GREP THE HOOK BEFORE DESIGNING;
this repo has had several "the mechanism is obvious" hypotheses turn out wrong.

DO NOT fix this by exempting tickets/ from the hook. Ticket bodies are exactly
where someone might paste a real key while describing an incident, and that is a
case the hook should still catch.

THE LIKELY RIGHT FIX, subject to the above: distinguish READING A .env FILE (the
actual hazard the hook exists for) from MENTIONING an env-related identifier in
prose. The former is a path/command shape; the latter is text. They are not the
same and the hook currently cannot tell them apart.

MUST-FIRE FIXTURE: an attempt to read or cat a real .env file is still blocked.
MUST-STAY-QUIET: a ticket whose text contains `import.meta.env`, `process.env`,
or `.env` as prose about configuration is written without obstruction.
THIRD FIXTURE: a ticket body containing something that genuinely looks like key
material is still refused.

ACCEPTANCE
- What the hook matches on, established by reading it, before any change.
- Reading-a-.env distinguished from mentioning-env-in-prose.
- tickets/ NOT blanket-exempted; state how the real case stays covered.
- All three fixtures committed.