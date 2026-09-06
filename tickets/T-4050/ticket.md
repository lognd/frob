---
id: T-4050
title: 'Scope denominator: five reported defects are one unanswered question about
  what set a ticket is accountable for'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: the deliverable is a stated model of what set
  a ticket''s scope is computed over; the five existing children carry the code scope'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FIVE INDEPENDENTLY-REPORTED DEFECTS ARE ONE UNANSWERED QUESTION: what set is a
ticket's scope computed OVER? Each was filed separately because each was reported
separately, but they disagree about the denominator in five different ways, and
five independent narrowings will conflict.

THE FIVE:
  T-3978  A scope glob matching zero TRACKED files is accepted silently, granting
          a write lease over nothing. Denominator: the filesystem, where it
          should be the git index. (Six instances, five of them mine.)
  T-4004  SCOPE001/002 are computed over the TRANSITIVE IMPORT CLOSURE, so a
          ticket with an EMPTY diff is already in violation, and adding one
          shared doc or test file to scope produces 30-367+ findings. Reported by
          a consumer, reproduced internally by my own implementer, and documented
          historically in T-3914's Done report -- a three-way arrival.
  T-4002  SUBTRACTIVE mirroring propagates a `scope --remove` from one worktree to
          the primary and destroys a sibling branch's declared scope. Denominator
          is right; the propagation direction is not.
  T-4032  SCOPE001 fires on a gitignored SYMLINK and on a TICKET THE RUN ITSELF
          FILED. Denominator includes untracked entries and frob's own ledger
          writes. (F-244 supplied the mechanism: `ticket new` in a worktree
          commits the ticket dir onto that branch, so it enters the diff.)
  T-4049  `--ticket X` findings are computed over the WHOLE BRANCH DIFF, so
          sibling tickets sharing a worktree contaminate each other's verdicts.
          Denominator is the commit range, not the ticket's own commits.

WHY THIS EPIC EXISTS RATHER THAN FIVE INDEPENDENT FIXES. Each ticket, taken
alone, suggests a local narrowing: use the git index; use direct doc/test edges
instead of the closure; do not mirror removals; exclude untracked files; use
per-ticket commits. Applied independently, at least three of those touch the same
code path and would each redefine the subject set in a different direction. The
coherent deliverable is ONE STATED ANSWER to "given ticket X, which files is X
accountable for, and by what evidence", from which all five follow.

THE ANSWER MUST COVER FOUR AXES, and each of the five tickets is a report about
exactly one of them:
  1. UNIVERSE      -- tracked files only (T-3978, T-4032)
  2. BREADTH       -- the diff plus direct doc/test edges, not the transitive
                      import closure (T-4004)
  3. RANGE         -- this ticket's own commits, not the whole branch (T-4049)
  4. PROPAGATION   -- which scope mutations mirror, and in which direction
                      (T-4002)

SEQUENCING GUIDANCE, not a mandate: T-4004 has the strongest corroboration (three
independent arrivals) and the largest measured cost, so the breadth axis is
probably first. T-3978 is the cheapest and is a pure guard. T-4002 is the only
one causing DATA LOSS and may deserve its narrow guard shipped ahead of the
design, as that ticket already states.

DO NOT CLOSE THIS EPIC BY FIXING THE FIVE. Its done-condition is the stated
answer plus the five children reconciled against it -- exactly the shape T-4037
is being built to enforce (a rule-shaped remediation must not be closable by
fixing instances). If the four axes are answered and the children then fall out
as consequences, that is success; five green tickets and no stated model is not.

ACCEPTANCE
- A written answer to "what set is a ticket's scope computed over", covering all
  four axes.
- Each of the five children reconciled against it, with any that become
  unnecessary explicitly dropped rather than silently closed.
- No axis left implicit because no consumer happened to report it.