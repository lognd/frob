---
id: T-2638
title: 'disclosure-remainder guard is lexical and blind to draft ids: rewording a
  heading defeats it, drafts can never satisfy it'
state: queued
kind: bug
origin: human
created: '2026-08-19'
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
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Two defects, and the second is the more important one

### Defect 1: the guard cannot see draft ticket ids

`src/frob/tickets/_reporting.py:831`

    _TICKET_ID_RE = re.compile(r"T-\d+")

Verified: this matches `T-2630` and does NOT match `T-draft-295a2473`.

The T-1648 disclosure-remainder guard requires a Done report containing
disclosure-shaped language ("not done", "deferred", ...) to carry a
`Filed:` line naming follow-up tickets. It collects those ids with the
regex above. So a ticket whose follow-ups are ALL drafts can never satisfy
it -- and drafts are not an edge case, they are the mandated workflow:
drafts renumber on land, and the agent playbook (section 0 item 8)
prescribes filing follow-ups as drafts.

Measured live on T-2623, a measurement-only ticket that filed 8 drafts
(which landed as T-2630..T-2637). Close refused, blocking a ticket whose
work was complete and correct.

### Defect 2 (the real one): the guard is LEXICAL, so rewording defeats it

The agent unblocked itself by RENAMING a heading:

    "### What was NOT done, and why"
        -> "### Scope boundary: measurement only, zero repairs (by design)"

No substantive content changed. The disclosure is still there, in the same
words, one heading down. The check simply no longer matched the phrase, so
it short-circuited and returned `None`.

That is a guard defeated by paraphrase. It fires on the presence of a
phrase, not on the presence of an undisclosed obligation -- so it is wrong
in BOTH directions: it blocked a ticket that HAD filed its follow-ups
(defect 1), and it can be silenced by anyone who rewords a heading without
filing anything.

This directly violates the standing repo directive that checks must parse
and compare SYMBOLS, never substring or regex matches -- a lexical match is
wrong in both directions, because comments match and aliases do not.

The agent disclosed the workaround fully and recommended this ticket, which
is the correct behavior. But the workaround should not have been available.

## Fix

- Make the id pattern recognize draft ids (`T-draft-<hex>`) as well as
  numbered ones, so the mandated draft workflow can satisfy the guard.
  This is the cheap half and unblocks the immediate case.
- Rework the disclosure detection so it does not hinge on matching prose
  phrases in a heading. The obligation the guard actually cares about is
  "this report describes work that was deferred and there is no filed
  ticket for it". Anchor on the structured record -- the ticket's own
  filed-followups field, its drafts, its evidence -- rather than on English
  in a heading. If a phrase heuristic must stay as a hint, it must not be
  the thing that decides.

## Do NOT

- Do NOT simply broaden the phrase list. A longer list of banned phrases is
  the same lexical mistake with more entries, and the next agent reworded
  their way past it in one attempt.
- Do NOT drop the guard. It is protecting something real: T-2588 left owed
  work recorded only in a waiver reason and never filed a ticket, which is
  precisely what this guard exists to catch.

## Positive controls, both directions

- a Done report deferring work, whose follow-ups are DRAFTS only, PASSES
  (defect 1's case)
- a Done report deferring work with NO follow-up filed at all is REFUSED --
  including when the disclosure heading is reworded to any wording. This is
  defect 2's case and it is the one that proves the fix
- a Done report with no deferred work and no follow-ups PASSES untouched --
  most reports are this shape and must not gain friction
- a Done report naming real numbered ticket ids still PASSES exactly as
  today
