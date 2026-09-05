---
id: T-3919
title: 'every HIGH in a consumer backend audit sat behind green gates: the false-negative
  list and ten ranked gate proposals'
state: queued
kind: security
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: epic
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
An external backend audit of a consumer repo (logand.app-v2, 2026-09-05) found
6 HIGH, 11 MEDIUM and 5 LOW security findings. EVERY HIGH SAT BEHIND GREEN FROB
GATES. Reported as their FROBLEMS F-096, sourced from
docs/security/audit-2026-09-05-backend.md in that repo (READ-ONLY -- do not
write there).

WHY THIS OUTRANKS THE REST OF TODAY'S CONSUMER QUEUE. Roughly ninety findings
arrived today and nearly all are frob firing WRONGLY -- over-broad rules, no-exit
waivers, lexical hooks. This is the opposite and rarer class: FROB NOT FIRING
WHEN IT SHOULD. An over-firing rule is visible and gets reported; a missing one
is silent by construction, and the only way to find it is an independent audit
of a real codebase. frob's own dogfooding structurally cannot produce this list,
because here frob is the subject rather than the thing being relied upon.

THE AUDITOR'S CONSOLIDATED LESSONS, ordered by how much of the report each would
have caught. Preserved close to verbatim because the ORDERING is itself the
finding -- it is a coverage ranking, not a wish list.

  1. WAIVER DEBT MUST NOT ACCUMULATE PAST A MILESTONE. Nearly every HIGH sits
     behind a frob:waive WIRE001 with a follow_up, or a frob:waive AFFECT001
     reasoned as an internal execution-model change. Individually honest;
     TOGETHER they let an entire auth subsystem exist un-wired while frob check
     stayed green. Proposal: waivers carrying a follow_up are ticket-scoped
     only; a milestone gate fails while any remain open; a count/age budget is
     reported per subsystem.
  2. PROTO001 -- protocol conformance at wiring sites. Two Protocols sharing a
     name plus a setattr on app.state. A rule that every consumer-side Protocol
     has a non-test implementation bound at a named wiring site would catch it,
     and also the in-memory-repos-in-production issue.
  3. RACE001 -- read-then-write on the same key/row inside one function with no
     lock, Lua, INCR-first or conditional UPDATE. Pair with a test obligation:
     any component whose spec row says cap / quota / single-use / idempotent
     needs a concurrent-callers test.
  4. DOCSTRING-DERIVED INVARIANTS. "in one transaction", "can be reached",
     "per-IP lockout check", "no loop is ever nested" were all FALSE CLAIMS.
     Auto-propose frob:invariant obligations from keywords in documented
     symbols (atomic / transaction / idempotent / single-use / constant-time /
     always / never) and demand evidence.
  5. FINER PII GRANULARITY IN STRATA. `carries` attaches atoms to a WHOLE
     STORE, so a password hash into an audit log and an email into a Redis key
     are invisible -- both stay inside a node already cleared for the atom.
     Needs a dataset construct under a store (per table, per keyspace) with its
     own carries, plus a taint rule from pii()-labelled columns into
     serializers, log extra= dicts and key-building f-strings.
  6. PROVENANCE FOR PII ATOMS. A derived_from edge would let SYS100 require
     that a single helper produce every client IP -- the highest-impact finding,
     and one no current gate can see because a wrong IP is still a string.
  7. GUARD-REGISTRY COMPLETENESS. Their own machine-checkable route inventory
     omits CSRF. Extend from "has an auth guard" to "every mutating route has
     an auth guard AND a CSRF guard, or is on a declared exemption list".
  8. ENVVAR002 -- every AppConfig field has a non-test reader. The existing
     three-way sync gate proves a field is DOCUMENTED, not that it DOES
     anything.
  9. LOOP001 -- asyncio.run inside a loop capturing outer state, plus a
     scheduler obligation to run two cycles.
 10. SCHEMA001 -- semantic field names require constrained types; plus a small
     lint for substring tests over request paths.

ITEM 1 IS ALREADY CORROBORATED FROM THE OTHER DIRECTION. Their F-082 reports
that nothing warns when one ticket accumulates dozens of deferral waivers, and I
recorded it as a MISSING SIGNAL with no demonstrated consequence. F-096 supplies
the consequence: invisible waiver concentration is what let a HIGH-severity
un-wired auth subsystem pass. Treat F-082 and item 1 as one piece of work, and
note that this moves it from "nice steering signal" to "evidenced cause of
security findings".

HOW TO USE THIS TICKET. Do NOT try to build all ten. This is a PARENT: decompose
into children, keep the auditor's ordering as the priority order, and file each
child with the specific finding it would have caught named in its body. The
ordering is evidence-backed coverage, so departing from it needs a reason.

THREE THINGS TO DECIDE EXPLICITLY BEFORE DECOMPOSING:
  - WHICH ITEMS ARE FROB RULES vs STRATA MODEL CHANGES. Items 5 and 6 change
    the .strata language (a dataset construct, a derived_from edge); the rest
    are gate rules. Those are different subsystems, different reviewers and
    different risk. Split accordingly.
  - WHICH ARE 1.0.0 AND WHICH ARE NOT. All 262 open tickets already default to
    milestone 1.0.0, so adding ten more without a call makes that number less
    meaningful, not more. Item 1 is arguably pre-alpha because it is a gate
    POSTURE change rather than new detection.
  - WHAT THE FALSE-POSITIVE COST IS for each proposed rule. RACE001 and
    LOOP001 in particular are heuristic shapes; a rule that fires on every
    read-then-write will be waived into uselessness within a week, which is the
    exact dynamic item 1 is about. Estimate before building.

DO NOT treat the auditor's proposals as specifications. They are a competent
outside reading of what would have helped, written without knowledge of frob's
internals -- some may already be partially implemented (check SYS100, PII010/012
and the invariant gate before building anything new), and some may be
unimplementable as stated. Verify each against what exists FIRST; "search the
code, not just the queue" applies with full force here.
