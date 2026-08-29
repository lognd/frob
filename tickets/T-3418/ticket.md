---
id: T-3418
title: DOC006 cannot express a citation that argues a command must not exist; waiving
  it measurably increased the error count 5 to 9
state: queued
kind: bug
origin: human
created: '2026-08-29'
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
- mode: set
  reason: 'the ticket documenting the DOC006 citation trap fell into it: de-backtick
    the three commands it quotes while explaining them'
  actor: logan
  at: '2026-08-29'
  old_length: 3732
  new_length: 3732
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOC006 has no way to express "this citation is an ARGUMENT AGAINST the command
existing". Its documented escape -- `frob:waive DOC006 reason="..."` for
intentionally external/illustrative/future-facing references -- is unusable for
that case, because any honest reason text must re-cite the same non-resolving
command and so produces MORE findings than it clears.

MEASURED 2026-08-29, by attempting exactly that fix and failing.

tickets/T-1382/ticket.md contains an owner-decision analysis whose conclusion is
"do not add "frob install-tool", "frob install", or a "frob make" passthrough".
`install-tool` is circular by construction: it is the command that INSTALLS
frob, so it can never be a frob subcommand. The analysis is correct and the
citations are the point of it.

DOC006 reports 5 errors against that file. I appended a `frob:waive DOC006`
with a reason explaining the above. Result:

    before waive:  5 DOC006 errors
    after waive:   9 DOC006 errors

Two independent failures in one attempt:
  1. The waive did not suppress the rule for those sites at all.
  2. The waive's own reason text cited "frob install-tool" / "frob install" /
     "frob make" while explaining why they must never be built, and DOC006
     counted those citations too -- four new findings at the waive's own lines.

I reverted the append via `frob ticket body --set-file` (NOT by hand-editing
tickets/T-1382/ticket.md) and re-measured: back to 5.

WHY THIS IS A RULE DEFECT AND NOT AN AUTHORING MISTAKE. The three ways to make
these five errors go away are all wrong:
  - Rewrite the citations to name real subcommands: inverts the argument.
  - Delete the citations: deletes the finding the ticket exists to record.
  - Waive: measurably makes it worse, per above.
That is a rule with no correct disposition available for a legitimate document.
Ticket bodies are the repo's design-argument record; arguing that an interface
must not exist is a normal thing for one to do.

WHAT TO DECIDE, explicitly -- there is a real argument for more than one:
  (a) Make the waive mechanism actually work for these sites, AND exempt the
      waive directive's own reason text from citation scanning. The second half
      is required; without it the mechanism stays self-defeating.
  (b) Give DOC006 a negative-citation form the author can use inline (some
      marker meaning "this name is discussed, not invoked").
  (c) Stop scanning `tickets/**` for cli-invocation pointers at all, on the
      grounds that ticket bodies are argument records rather than user-facing
      docs. Cheapest, and it loses real coverage -- a ticket that tells an
      agent to run a command that does not exist IS worth catching, and this
      repo has had exactly that failure.
I lean (a), because the reason-text exemption is a bug regardless of which
option is chosen, but state the reasoning rather than inheriting mine.

CHECK FIRST, do not assume: confirm WHY the waive failed to suppress. It may be
that waive directives are not honoured inside tickets/** at all, or that the
directive needs different placement relative to the cited line. That answer
changes which option is even available.

MUST-FIRE FIXTURE:   a ticket body telling a reader to run a command that does
                     not exist is still flagged.
MUST-STAY-QUIET:     a ticket body arguing a command must NOT exist is not
                     flagged, and neither is the waive's own reason text.

ACCEPTANCE
- The reason-why-the-waive-failed answered with a file:line, not inferred.
- The chosen option stated with reasoning.
- Both fixtures committed. The must-fire one matters most here: the easy fix is
  to stop scanning ticket bodies, and that would silently drop real coverage.
