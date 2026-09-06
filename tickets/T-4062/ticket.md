---
id: T-4062
title: 'frob check --ticket passes and the land then refuses on COV002: the scoped
  check is used as a prediction of the unscoped pre-commit sweep'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
Consumer apollo, 2026-09-06:

  "T-1514 pre-commit unscoped sweep: LAND CAN BE REFUSED FOR COV002 on symbols
   the implementer changed but did not edge (call-site methods, class App) EVEN
   WHEN `frob check --ticket` PASSED IN THE WORKTREE EARLIER. The refusal is
   pre-commit (staged squash unwound, nothing lands) -- fix is add edges on every
   changed symbol, restamp, re-land."

TWO CHECK SURFACES DISAGREE ABOUT THE SAME TICKET. The agent ran the check frob
offers for exactly this purpose, got a pass, and the land then refused on a rule
that check did not report. So `frob check --ticket` cannot be used to predict
whether a land will succeed -- which is the one thing an implementer needs from
it before committing to a land.

THE MECHANISM IS NAMED IN THE REPORT AND IS NOT A BUG IN EITHER SURFACE: the land
runs an UNSCOPED pre-commit sweep (T-1514), while `--ticket` is SCOPED. So the
land legitimately sees symbols the scoped check never examined -- call-site
methods and a class the implementer touched but did not declare. Both surfaces
are behaving as designed. THE DEFECT IS THAT NOTHING SAYS THEY ANSWER DIFFERENT
QUESTIONS, so the narrower one is used as a proxy for the wider one.

THIS IS THE "THREE SURFACES, THREE CHECK SETS" PROBLEM WITH A MEASURED COST. This
repo has long carried the observation that CI gates-fast, `land --dry-run` and a
real land each run different subsets with no documented relationship. Apollo has
now paid for it: a full land attempt built, staged, squashed and then unwound,
with the work still not landed and a restamp/re-land cycle required.

WHAT TO BUILD, in order:
1. DOCUMENT THE RELATIONSHIP FIRST -- which surfaces run which rule sets over
   which subject sets. This is a statement, not code, and it is the deliverable
   that makes the rest decidable. Until it exists, every fix is guesswork about
   what the surfaces are FOR.
2. MAKE THE NARROW SURFACE SAY WHAT IT DID NOT CHECK. `frob check --ticket`
   should state that it examined only the ticket's scope and that the land will
   additionally run an unscoped sweep. A user who knows the check is partial will
   not treat it as a prediction; today nothing signals the gap.
3. ONLY THEN consider making them agree. A `--dry-run`-style mode that runs the
   LAND's rule set is the obvious candidate, but note the cost: the unscoped
   sweep is expensive, which is presumably why `--ticket` is scoped in the first
   place. Do not make the fast surface slow without deciding that trade
   deliberately.

DO NOT fix this by dropping the unscoped sweep. It caught real COV002 gaps here --
symbols genuinely changed without edges. The sweep is doing its job; the problem
is that its scope is invisible until it refuses.

RELATED, ALREADY FILED: T-4004/T-4050 concern what set scope is computed OVER for
a given ticket. This is adjacent but distinct -- it is about which SURFACE applies
which set, not about the set's boundaries. Do not merge, but read T-4050 first
since a stated model of "the ticket's subject set" would make this document much
easier to write.

ALSO NOTED FROM THE SAME REPORT, no action needed: WAIVE004's auto-fix refuses to
delete when five or more waivers of one rule go stale at once (a degraded-run
guard). Apollo calls it "correct behavior, loud message" -- recording it because
a guard working as intended is worth knowing about when auditing this area, and
because it is the same shape as the WAIVE004 escape that once deleted 55 live
waivers.

MUST-FIRE FIXTURE: a ticket that will be refused by the land's unscoped sweep is
not reported as clean by the narrow check without a stated caveat.
MUST-STAY-QUIET: a genuinely clean ticket still passes both surfaces.

ACCEPTANCE
- A written statement of which surfaces run which rule sets over which subjects.
- The narrow check discloses what it did not examine.
- Any move toward agreement made with the cost of the unscoped sweep stated.
- Both fixtures committed.