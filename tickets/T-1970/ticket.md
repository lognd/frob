---
id: T-1970
title: 'No way to mention a frob directive without using it: prose blocked two lands,
  and no escape syntax exists'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). The frob comment DSL has no way to
MENTION a directive without USING it, and no escape syntax exists
anywhere in the codebase (searched for escape/verbatim/literal-directive
handling in `frob.gates._waive_comments` and `frob.lang` -- the only
"escape" hits are unrelated tree-sitter escape hatches).

This produces two opposite failures with one root cause:

OVER-PARSE (code comments). Prose ABOUT a directive is parsed AS one and
refuses the land. Measured, two consecutive refusals by one agent while
landing T-1956, neither a code bug:
  1. `TicketError.LiveTrackerCited` (frob.tickets._evidence:637,
     frob.tickets._land:2664) -- the agent's discharge comment contained
     the literal text `follow_up="T-1956"` while EXPLAINING that the
     follow-up had been discharged. The live-tracker text scan read its
     own discharge note as an active citation.
  2. `DSL001` -- the reworded replacement comment contained the literal
     substring `frob:waive WIRE001` while describing the waiver being
     removed, and was parsed as a malformed directive.
Both were fixed by rewording English prose to avoid substrings, not by
changing any code. The author's only recourse is to describe the DSL
without ever spelling it correctly.

UNDER-PARSE (markdown). The mirror image, filed separately as T-1968:
`<!-- frob:waive DOC006 ... -->` in `docs/modules/fuzz.md:28` and
`<!-- frob:waive INV003/INV004 ... -->` in `docs/modules/deploy.md:4-5`
(deliberate T-1023 burn-down output) are never parsed at all, so they
suppress nothing and nothing says so.

So the same construct is treated as live where it is meant as prose, and
as prose where it is meant as live. Both are the missing mention/use
distinction.

WHY IT COSTS THROUGHPUT: every discharge comment, every done-report
explaining a waiver, and every doc page documenting the DSL is a
potential land refusal. It also actively degrades documentation quality,
since the workaround is to write the directive wrongly on purpose --
which then teaches the wrong syntax to the next reader, agent included.

DO NOT FIX IT THIS WAY:
- Do NOT loosen the scanners so that a directive must be at line start,
  or must be the only content, or similar positional narrowing. Real
  directives legitimately appear mid-comment and trailing, and narrowing
  would silently stop honoring live waivers -- the failure mode where a
  "safe" cleanup once deleted 55 live waivers.
- Do NOT special-case the words "discharged"/"removed"/"was" near a
  citation. That is heuristic prose-sniffing; it will both miss cases and
  create new false negatives on genuine directives.
- Do NOT rely on the current workaround (reword the prose). It is what
  the two refusals above already cost, it is unteachable, and it makes
  correct documentation of the DSL impossible.

FIX DIRECTION: an explicit, boring escape that means "this is a mention,
not a directive" -- e.g. a doubled prefix (`frob::waive`) or a
`frob:quote` wrapper -- recognized by EVERY scanner (waiver validation,
live-tracker citation scan, DSL001 validation), and documented in the DSL
reference. One escape, honored everywhere, so a new scanner cannot forget
it. Pairs with T-1968: that one makes an ignored directive loud, this one
makes a mentioned directive quiet.

ACCEPTANCE: first test must FAIL before the fix -- a comment containing
an escaped mention of `frob:waive WIRE001` and of `follow_up="T-####"`
must not trigger DSL001 or LiveTrackerCited, and must not block a land.
Then assert an UNESCAPED real directive on the same line still parses and
is still honored (no weakening), and that the escape is recognized by
each scanner independently, not just the first one fixed.
