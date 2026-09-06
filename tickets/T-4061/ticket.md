---
id: T-4061
title: 'F-265: close''s own remedy text instructs the ledger-v1 inline heading that
  close then refuses, and never names frob ticket done-report'
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
Consumer logand.app-v2 F-265, 2026-09-06:

  "T-0237's agent wrote the done report as a `## Done report` heading in
   ticket.md's body; close REFUSED until a separate tickets/T-xxxx/done-report.md
   existed. The playbook says done-report.md, but the verb's error should name the
   expected path instead of failing on 'missing done report' when a section with
   that title IS PRESENT."

FROB'S OWN ERROR MESSAGE TELLS THE USER TO DO THE THING FROB THEN REFUSES. This
is worse than the consumer realised, and it is verified in our source.
src/frob/app/ticket_runner/_close_cmd.py:66-73 builds the remedy text for exactly
this failure:

    f"{verb} failed: {err} -- {ticket_id} is missing evidence or a "
    f"Done report -- add evidence (...) and write a '## Done report' heading "
    f"under {ticket_id}'s section in tickets.md"

So the message instructs the INLINE-HEADING-IN-tickets.md form. That is the
LEDGER v1 shape. Under ledger v2 the done report is a separate file,
tickets/T-xxxx/done-report.md, written by `frob ticket done-report`. The
remediation text was never migrated, so it now directs users into precisely the
state that produces the refusal it is attached to.

I HIT THIS MYSELF EARLIER TODAY. Closing T-3934 produced that exact message. I
ignored its instruction and used `frob ticket done-report --why-file`, which
worked. An agent that BELIEVES the message -- as this consumer's did, and as one
of theirs did on F-253 -- gets stuck.

WE ALREADY KNEW AGENTS HAND-TYPE THIS HEADING, AND FIXED IT IN A SIBLING PATH.
src/frob/app/ticket_runner/_mutate.py:510-525 carries T-3468's "DEFECT 3" note
verbatim: "an agent hand-typing a '## Done report' heading into `body --append`
(the workaround for the dedicated verb not existing, or not knowing it does) hits
this refusal with no pointer to the verb that exists specifically to write this
heading correctly -- name it here rather than leaving the generic message stand
alone." That fix names `frob ticket done-report` in the BODY path. THE CLOSE PATH
WAS MISSED. So the remedy is already designed and precedented; it simply was not
applied everywhere the confusion arises.

THREE THINGS TO FIX, in order:
1. THE CLOSE REMEDY TEXT must name `frob ticket done-report` and the real path
   (tickets/<id>/done-report.md), not a tickets.md section. This alone resolves
   the report.
2. SWEEP FOR OTHER LEDGER-v1 REMEDIATION TEXT. If this message survived the v1->v2
   migration, others may have. Grep for remediation strings mentioning tickets.md
   and check each against how the ledger actually works now. Report the count
   even if it is one.
3. CONSIDER RECOGNISING THE INLINE FORM, but only after (1). The consumer's own
   framing is "the error should name the expected path", not "accept my heading" --
   they are asking to be told the truth, not for a second supported shape. Note
   _tickets_gate.py:665 already has a regex matching `## Done report` headings, so
   detection is possible; DECIDE DELIBERATELY whether a second accepted form is
   wanted rather than adding one because it is easy. Two supported shapes for one
   artifact is how the frob:tests direction ambiguity (T-4059, T-4014) started.

MUST-FIRE FIXTURE: closing without a done report produces a message naming
`frob ticket done-report` and the real file path.
MUST-STAY-QUIET: a ticket with a proper done-report.md still closes.
THIRD FIXTURE: no remediation string in the close/reverify paths instructs a
ledger-v1 shape -- asserted against the current ledger layout, so a future
migration cannot silently strand another message.

ACCEPTANCE
- The close remedy names the correct verb and path.
- A sweep for other surviving v1-era remediation text, with the count reported.
- Any decision to accept the inline form made deliberately, not incidentally.
- All three fixtures committed.