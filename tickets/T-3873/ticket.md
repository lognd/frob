---
id: T-3873
title: frob ticket reopen writes a Reopen log subsection that frob ticket close rejects
  as an undisclosed follow-up
state: queued
kind: bug
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as typani FROBLEMS T-022. frob writes content that frob then rejects.

SEQUENCE: close T-0017 -> reopen --reason ... -> fix -> done-report -> close.

OBSERVED on that final close:

    Done report contains disclosure-shaped language ("non-standard
    Done-report subsection ('Reopen log')") but no 'Filed:' line names a
    follow-up ticket

The "Reopen log" subsection was written by `frob ticket reopen` ITSELF, not by
the author. The disclosure check then reads frob's own generated heading as an
undisclosed follow-up and refuses the close. Workaround was to hand-add
"Filed: none -- ..." to satisfy a check about content the author never wrote.

WHY THIS IS THE SAME DEFECT CLASS AS SEVERAL OTHERS TODAY, and worth fixing as
such rather than as a one-off: two verbs disagree about the ledger's own format.
The producer and the consumer of a generated artifact hold different contracts.
Already seen today:
  - T-3852: `close` demands evidence a container ticket cannot own; binding a
    leaf's then fails EvidenceScopeUnbound. Two gates, no exit.
  - typani T-006/T-009: `done-report` diffs committed history while `close`
    accepts a report written before the work was committed, so the documented
    order is wrong and costs three failed closes to rediscover.
  - this one: `reopen` writes a subsection `close` rejects.
In every case each rule is individually defensible and the COMPOSITION is
broken. Say so in the done report; the pattern is the finding.

THE FIX -- decide which side owns it, and state why:
  (a) The disclosure check exempts frob-generated subsections. Requires a way to
      tell generated from hand-written content. If there is no marker today,
      adding one is the real work and is worth doing: a generated Done-report
      section that cannot be distinguished from an author's prose will cause
      this again in some other check.
  (b) `reopen` writes the "Filed:" line itself. Cheaper, but it makes reopen
      assert something about follow-ups it does not actually know, and a
      "Filed: none" that frob wrote is a claim no human made. Prefer (a) unless
      (a) is genuinely blocked.
I lean (a) with a generated-content marker. If you choose (b), say explicitly
what the auto-written line means and why an unattested claim in the audit trail
is acceptable here.

DO NOT relax the disclosure check generally. It exists so a Done report that
hints at deferred work names the ticket carrying it -- that is a real guard
against work vanishing between a close and nothing. Narrow the exemption to
frob's own generated content; do not weaken the rule for author prose.

CHECK WHETHER OTHER VERBS GENERATE DONE-REPORT CONTENT that could trip the same
check. `reopen` is the reported one. Enumerate every verb that writes into a
done report or ticket body and report which of them produce disclosure-shaped
text. That list is the durable output; fixing only "Reopen log" leaves the next
one to be found by another consumer repo.

MUST-FIRE FIXTURE:   an AUTHOR-written non-standard subsection with no 'Filed:'
                     line still refuses the close.
MUST-STAY-QUIET:     a reopen-generated "Reopen log" subsection closes cleanly
                     with no hand-added line.

ACCEPTANCE
- The (a)/(b) choice stated with reasoning.
- The generated-vs-authored distinction implemented, if (a).
- The enumeration of verbs that write done-report content, with a verdict each.
- Both fixtures committed. The must-fire one is the one that matters: an
  exemption that also silences author prose would remove the guard entirely.
