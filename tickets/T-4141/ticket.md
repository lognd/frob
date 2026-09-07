---
id: T-4141
title: 'close refuses a Done report that says no follow-up is needed: the phrase list
  contains that exact negation, so declaring nothing to file reads as failing to file'
state: queued
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
- src/frob/tickets/_reporting.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a Done report stating no follow-up is needed with a reason and no Filed
    line, when the ticket is closed, then the close succeeds
  evidence: []
- text: given a Done report genuinely disclosing unfinished work with no Filed line,
    when the ticket is closed, then the close is still refused
  evidence: []
- text: given a phrase describing work not addressed because it was already handled
    elsewhere, when the ticket is closed, then the close is not refused
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
SAYING THERE IS NOTHING TO FILE IS TREATED AS FAILING TO FILE SOMETHING. Reported
as logand.app-v2 F-344: an agent's Done report stated that no follow-up was
needed; close refused until the sentence was reworded. Their proposed fix is
right and is one line of intent: match on an explicit ticket-id pattern, not on
the words.

I CONFIRMED THE MECHANISM AND IT IS EXACTLY AS BAD AS IT SOUNDS. The literal
string "no follow-up" is a member of `_DISCLOSURE_PHRASES` in
src/frob/tickets/_reporting.py (around line 913), alongside genuine disclosure
markers like "not implemented", "still outstanding" and "left unfinished". So
"no follow-up needed" matches, `_undisclosed_remainder_reason` in
src/frob/app/ticket_runner/_close_cmd.py demands a Filed: line naming a real,
open ticket, and the author has none to give BECAUSE THEY JUST SAID THERE IS
NOTHING TO FILE.

THE PHRASE IS SEMANTICALLY INVERTED RELATIVE TO EVERY OTHER MEMBER OF THE LIST.
Every other entry asserts that work REMAINS. This one asserts that none does.
Matching it as a disclosure marker is not a tuning problem, it is a sign error.

IT IS A NO-EXIT, and a particularly unpleasant one. The remedy the refusal names
-- file a follow-up ticket -- is precisely the action the author has determined
is unnecessary. The available responses are: file a junk ticket to satisfy the
gate, or reword an accurate sentence into a less accurate one. The consumer chose
the second. Both make the record worse, which is the wrong-incentive class:
the cheapest way to clear this gate degrades the Done report.

IT IS ALSO THE LEXICAL-HOOK CLASS, and this repo has a standing directive that
checks must compare structure, never substring. What makes this instance sharp is
that THE MIGRATION HAS ALREADY HAPPENED HERE AND THIS LIST WAS LEFT BEHIND. The
comment immediately below the phrase list (T-2638) says the real anchor
`disclosure_shaped_language` decides on markdown heading SYNTAX under the Done
report section, "never the heading's own wording", and that the phrase list stays
live only as "a widening hint" for plain-prose disclosures. So the structural
check exists; the lexical list is a legacy widener; and it is the widener that
fires here. A hint that produces false refusals is not widening coverage, it is
manufacturing findings.

WHAT TO DO
  1. Remove "no follow-up" from the phrase list. It cannot be repaired by
     tightening -- the string's meaning is the negation of what the list is for.
  2. Audit the remaining twelve entries for the same sign error, and for
     substring capture generally. Note "not addressed" is a substring of "not
     addressed in this ticket because it was already addressed upstream", and
     "did not fix" matches "did not fix X because X was not broken". Report which
     entries survive the audit and why.
  3. Decide whether the lexical widener should exist at all now that the
     structural anchor does. If it stays, it must be documented as
     hint-only-never-refusing, and the refusal path must key on the structural
     anchor. If a hint can refuse a close, it is not a hint.
  4. Whatever remains, the refusal message must quote the matched phrase AND say
     that a phrase match alone is not proof of undisclosed work, so the author
     can tell a real finding from a false one. It already names the phrase; it
     does not say the second part.

MUST-FIRE FIXTURE:   a Done report stating that no follow-up is needed, with a
                     reason and no Filed line, closes successfully.
MUST-STAY-QUIET:     a Done report genuinely disclosing unfinished work with no
                     Filed line is still refused -- the T-1420 incident this
                     guard exists for must stay caught.
THIRD FIXTURE:       a negated form of another listed phrase (for example, work
                     described as not addressed BECAUSE it was already handled
                     elsewhere) does not refuse the close.

ACCEPTANCE
- The inverted phrase removed, not merely reordered or reweighted.
- The other twelve entries audited for sign errors and substring capture, with
  the result reported per entry.
- The hint-versus-refusal question decided: a hint must not be able to refuse.
- The refusal message states that a phrase match is not itself proof.
- All three fixtures committed.
