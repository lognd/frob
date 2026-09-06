---
id: T-4020
title: 'F-234: frob''s own runtime messages cite doc anchors nothing validates, and
  one is dead (DOC006 checks prose, not message strings)'
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
- src/frob/tickets/_leases.py
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
Consumer logand.app-v2 F-234, 2026-09-06. Two sub-findings; the first is a
systemic coverage gap and is the reason this ticket is worth more than its size.

SUB-FINDING 1 -- A DEAD DOC ANCHOR IN OUR OWN RUNTIME MESSAGE. Verified:

  the real heading, docs/guides/agent-playbook.md:99
      ## 1. Worktree warm-up (do this FIRST, every time)
  which anchors as
      #1-worktree-warm-up-do-this-first-every-time
  and docs/modules/tickets-lifecycle.md:1016 cites it CORRECTLY, in full.

  But src/frob/tickets/_leases.py:1592 and :1625 emit the TRUNCATED
      (docs/guides/agent-playbook.md#1-worktree-warm-up)
  to the user. That anchor does not resolve.

THE GAP IS THE POINT, NOT THE TYPO. DOC006 exists precisely to catch pointers
that do not resolve, and it caught several in ticket prose during this very
session -- including two of mine. It does not look inside PYTHON STRING LITERALS
that are user-facing messages. So frob enforces on everyone's prose a standard it
does not apply to its own output, and the proof is that the correct anchor and
the broken one live in the same repo, one in a doc (checked) and one in a message
(unchecked).

THAT CLASS IS WORTH SWEEPING. Any `docs/...#anchor` or `docs/...md` string
emitted by the CLI is a promise to the user that a document exists and says
something. Those promises rot exactly like the ones in markdown, and nothing
currently notices. Enumerate the doc references embedded in runtime messages
across src/ and report the count and how many resolve -- the answer to "how many
of our error messages point at documentation that is not there" is itself the
deliverable, whether it is one or forty.

DO NOT just fix the two lines. Fixing the reported instance and leaving the class
unchecked is what allowed a correct citation and a broken one to coexist.

SUB-FINDING 2 -- "495 COMMITS BEHIND MAIN" ON A PARKED-BRANCH WORKTREE. This is
the same wrong-denominator defect already filed as T-3943 (F-173): distance is
measured against main rather than against the branch the ticket actually targets.
On a deliberately parked branch that number is not a warning, it is noise, and it
appears at `ticket start` -- the first thing an agent sees. CROSS-REFERENCE
T-3943 rather than fixing this separately; if T-3943 lands, re-measure this
before doing anything. Note the two are not identical: T-3943 is about the diff
base used by gates, this is about a staleness warning at start, but if both
derive "the branch this ticket targets" they should derive it from one place.

MUST-FIRE FIXTURE: a runtime message citing a non-existent doc anchor is flagged.
MUST-STAY-QUIET: a runtime message citing a real anchor is not.
THIRD FIXTURE: the two _leases.py citations resolve.

ACCEPTANCE
- Doc references embedded in runtime messages are checked by something, not by
  hand; the count found and how many resolved, stated.
- The two cited lines corrected to the full anchor.
- Sub-finding 2 cross-referenced to T-3943, not fixed twice.
- All three fixtures committed.