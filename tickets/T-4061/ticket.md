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
body_changes:
- mode: set
  reason: 'F-266 adds a second unnamed micro-grammar in the same path: a ''### Filed''
    subsection saying none is rejected while only a literal ''Filed: none'' line passes,
    with no error naming the accepted form. Widens this ticket from one stale string
    to the done-report path''s undocumented grammars'
  actor: logan
  at: '2026-09-06'
  old_length: 3836
  new_length: 6347
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
## A SECOND UNNAMED GRAMMAR IN THE SAME PATH: F-266

logand.app-v2, 2026-09-06 (their T-0015). The first half re-reports F-265 above
(inline `## Done report` silently insufficient, generic error). The second half
is a DIFFERENT detector with the IDENTICAL defect shape:

  "A `### Filed` subsection saying 'none' trips the disclosure-language detector
   expecting a ticket id; only a literal `Filed: none` line passes. THE ERROR
   SHOULD QUOTE THE ACCEPTED GRAMMAR."

So the done-report path now has TWO places where a reasonable, human-sensible
shape is rejected by an exact-form matcher whose error does not state the form it
wants. A `### Filed` heading followed by "none" and a `Filed: none` line mean the
same thing to any reader; only one parses, and the message does not say which.

THAT GENERALISES THIS TICKET. It was filed as "one stale remediation string";
with F-266 it is better read as: THE DONE-REPORT PATH ENFORCES SEVERAL UNDOCUMENTED
MICRO-GRAMMARS AND ANNOUNCES NONE OF THEM. Widen the deliverable accordingly --
enumerate every shape the done-report/disclosure machinery matches on
(the report heading, the Filed disclosure, and anything else in that parser), and
for each: state the accepted grammar IN THE ERROR when it does not match.

WHY THE MESSAGE MATTERS MORE THAN THE GRAMMAR HERE. Whether we accept `### Filed`
+ "none" is a judgement call and arguably not worth changing. What is NOT a
judgement call is that a user who writes it gets an error that does not tell them
what to write instead -- so the only route to compliance is reading our source or
guessing. This repo has now collected four instances of that exact failure today
(T-4053 help text denying the path that works, T-4020 a runtime message citing a
dead anchor, T-4061's ledger-v1 instruction, and this), and in two of them an
agent ABANDONED CORRECT WORK because it believed the message.

NOTE THE LEXICAL SMELL, worth checking while in there: "only a literal
`Filed: none` passes" suggests a substring or line-prefix match rather than a
parsed structure. That is the lexical-hook class this repo tracks at nine
instances. If the disclosure detector is matching text rather than parsing the
report's structure, say so -- it may deserve its own fix rather than a better
error message.

ADDITIONAL ACCEPTANCE
- Every micro-grammar the done-report/disclosure path enforces, enumerated.
- Each mismatch error states the accepted form, quoting it.
- Whether the disclosure detector is lexical or structural, answered.
