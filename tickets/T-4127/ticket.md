---
id: T-4127
title: SCOPE002 explodes on hub files (design/frob.strata, docs/modules/gates.md)
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: T-4665
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4665
  reason: '2026-09-19: SF-18 in the STRATA friction audit; joins story B of epic T-4662'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: 'folds in T-4121 (consumer report F-308, dropped as a duplicate of this
    better-located ticket): the consumer reverted a correct doc fix rather than widen
    scope, and three independent agents measured the same explosion at 140, 345 and
    71 on 2026-09-06, which settles the population question this repo needed answered
    before choosing a design'
  actor: logan
  at: '2026-09-06'
  old_length: 2079
  new_length: 5752
- mode: set
  reason: 'records the queue census: 9 open SCOPE002-titled tickets, 4 filed today
    by 3 different agents who each hit the explosion while working something unrelated.
    Documents why T-4123/T-4128/T-4129 are blocked on this cause fix rather than worked
    as doc debt, and warns against assuming the five older ones are duplicates without
    reading them'
  actor: logan
  at: '2026-09-06'
  old_length: 5752
  new_length: 7809
- mode: set
  reason: 'adds a sixth independent measurement (267 warnings from one shared design
    doc) and the consumer''s own framing of the mechanism, plus the point their report
    adds that mine did not: the hub-file shape is deliberate documentation design,
    so any fix premised on splitting those documents asks consumers to reorganise
    their docs to suit a gate'
  actor: logan
  at: '2026-09-07'
  old_length: 7809
  new_length: 9988
- mode: append
  reason: '2026-09-19: attaching SF-18''s evidence row verbatim plus a FRESH fourth
    and fifth measurement taken while filing epic T-4662 -- 587 scope-closure warnings
    on a ticket with an EMPTY scope, which disproves the assumption that only tickets
    touching design/frob.strata are affected'
  actor: logan
  at: '2026-09-19'
  old_length: 9988
  new_length: 12228
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4110 (H3-10/SYS113): design/frob.strata (26 nodes,
each with its own frob:doc pointing at a different unrelated doc file --
roadmap.md, threat.md, cli.md, serve.md, mutate.md, host.md, several
guides/*) and docs/modules/gates.md (the master rule catalog, describing
essentially every gate module in src/frob/gates/**) are both maximal
cross-reference hubs. frob.toml promotes SCOPE002 to Severity.ERROR
([gates.severity] SCOPE002 = "error"), and SCOPE002's own closure check
(_scope002_edge_gap_violations / scope_doc_code_gaps) evaluates EVERY
symbol in a scoped FILE, not just the symbols a ticket's diff actually
touches.

Measured directly: adding design/frob.strata + docs/modules/gates.md to
T-4110's scope (needed because the ticket must remove one dead via
entry and add two new test files to two existing via lists in
design/frob.strata, plus a new rule-catalog section in gates.md) produced
141 SCOPE002 findings naming ~140 distinct unrelated files (docs/strata/
roadmap.md alone accounts for 134 symbols; the rest is nearly the entire
src/frob/gates/**.py tree via gates.md). frob check --ticket then FAILs
gate:SCOPE unconditionally for ANY ticket that touches either hub file,
regardless of how small the actual diff to it is.

This cannot be the intended behavior: a one-line addition to a shared
rule catalog or a two-line via-list edit in the self-model should not
require a ticket to also take ownership of that catalog's entire
reverse-doc-closure. Proposed fix (one of):
- SCOPE002's edge-gap check narrows to symbols the ticket's OWN diff
  hunks actually touch (or are newly introduced by), not every symbol
  the scoped FILE happens to contain -- matching SCOPE001's own
  per-touched-file (not per-scoped-file) granularity.
- Or: an explicit hub-file exemption list (config-driven, like
  [graph].exclude) for files whose reverse-doc-closure is provably
  larger than any single ticket could reasonably absorb.

Filed rather than fixed silently or worked around by disproportionately
widening T-4110's scope to ~140 unrelated files.

THIS IS ALSO A CONSUMER-REPORTED DEFECT, AND T-4121 WAS FILED FOR IT SEPARATELY
BEFORE THIS TICKET EXISTED. T-4121 is now dropped in favour of this one, which
locates the mechanism precisely where T-4121 only described it. Its content is
folded in here so nothing is lost.

THE CONSUMER REPORT (logand.app-v2 F-308): editing ONE ROW of a shared doc table
caused the scope gate to demand that every symbol anchored anywhere in that
document be in the ticket's scope. Their agent REVERTED the correct one-sentence
doc fix rather than widen scope that far.

THAT REVERSION IS THE FINDING, and it is what raises this above a friction
report. A gate whose cheapest clearing action is to abandon a correct
documentation fix has made the record worse -- the wrong-incentive class. It does
so specifically to the smallest and safest kind of doc change, a one-row
correction, which is the change we most want people to make freely.

THREE INDEPENDENT MEASUREMENTS OF THE SAME EXPLOSION, all on 2026-09-06:
    ~140 unrelated files   this ticket's own measurement, from T-4110
     345 closure warnings  a planner scoping an unrelated leaf to the gates
                           catalog; it dropped the catalog from every leaf's
                           scope and left the doc as an unscoped append at close
      71 closure warnings  filing T-4121 itself, scoped to two closure modules
Three different agents, three different tasks, one file. The population question
is settled for this repo: hub files exist here and the explosion is routine.

WHY FILE GRANULARITY IS THE WRONG UNIT HERE. Scope closure is right in general --
edit the doc a symbol is anchored to and you are implicitly touching that
symbol's contract. It breaks down for a file that is a TABLE OF INDEPENDENT ROWS,
each anchored to a different symbol. There, file granularity asserts a coupling
that does not exist: editing row 40 says nothing about row 3. The closure
computes a true statement about the FILE and a false one about the CHANGE.

EVALUATE THE DIFF-SCOPED OPTION FIRST, ahead of any new declaration syntax. The
diff already says which lines changed and each anchor's position in the file is
already known, so narrowing the closure to the anchors the diff actually touches
needs no new syntax and no consumer action. A fix consumers must adopt is a fix
most of them will not get. Row-granular doc ownership -- which the consumer
proposed, and which they note would also fix the lease collisions they reported
separately on the same files -- is the fallback if the diff-scoped option fails.
If it is adopted, confirm or refute their claim that one mechanism causes both
symptom families.

NOTE WHAT BOTH SIDES HAVE BEEN DOING INSTEAD, because both workarounds degrade
the record and neither should survive the fix: they revert correct edits; we drop
the hub file from scope and patch it as an unscoped append at close time.

MUST-FIRE FIXTURE:   a one-row edit to a hub file carrying anchors for many
                     symbols requires only the edited row's symbol in scope.
MUST-STAY-QUIET:     an edit to a doc section that genuinely covers several
                     symbols still requires all of them -- the closure must not
                     become a blanket escape.
THIRD FIXTURE:       an edit to a single-symbol doc file behaves exactly as today.

ACCEPTANCE
- The diff-scoped option evaluated first and either adopted or ruled out with a
  stated reason.
- A ticket touching one row of either named hub file no longer pulls the rest of
  the file's anchors into scope.
- The lease-collision symptom on the same files checked against the chosen fix.
- All three fixtures committed.

THE QUEUE CENSUS, MEASURED 2026-09-06, AND IT IS THE STRONGEST ARGUMENT ON THIS
TICKET. Counting tickets whose TITLE names this rule:

    9 open      T-3299, T-3902, T-3926, T-3957, T-4098, T-4123, T-4127,
                T-4128, T-4129
    8 done
    2 dropped today as duplicates (T-4121, T-4122)

FOUR OF THE NINE OPEN ONES WERE FILED TODAY, by three different agents working
three unrelated tickets. Not one of them set out to work on this rule. Each hit
the explosion while doing something else, correctly declined to widen scope to
satisfy it, and filed the debt.

THAT PATTERN IS THE FINDING. A gate that reliably produces a ticket which is
never fixed is not measuring debt -- it is manufacturing it. Nineteen tickets
across the rule's life, with eight closed and the population still growing, says
the closing does not keep up and never will, because every future ticket touching
a hub file mints another one.

I HAVE BLOCKED T-4123, T-4128 AND T-4129 ON THIS TICKET RATHER THAN DROPPING
THEM, and the distinction matters. They are kind=docs tickets asking someone to
declare the missing doc edges -- clearing the symptom. This ticket fixes the
cause. If the diff-scoped closure lands, those symbols were never legitimately in
any ticket's scope, so the debt they describe stops existing rather than getting
paid. Working them FIRST would mean writing doc declarations for dozens of
unrelated symbols to satisfy a question the gate should not have asked -- the
wrong-incentive action this ticket exists to stop. Re-evaluate all three after
this lands; the expected outcome is that they are dropped, not worked.

DO NOT TREAT THE OLDER FIVE (T-3299, T-3902, T-3926, T-3957, T-4098) AS
AUTOMATICALLY DUPLICATE. I have not read them and they may describe genuinely
different SCOPE002 behaviour -- T-4098 in particular is about the rule being
structurally UNWAIVABLE, which is a separate defect from the closure being too
broad. Read each before folding or dropping it; a census is evidence of a
pattern, not proof that every member is the same bug.

A SIXTH MEASUREMENT, AND THE CONSUMER'S OWN CONCLUSION IS THE ARGUMENT.
logand.app-v2 F-370: adding one shared design document to a ticket's scope -- the
ticket needed it because its acceptance criteria update one component's anchor --
produced roughly 267 closure warnings naming symbols from a completely different
subsystem that the ticket never touches.

Their one-line statement of the mechanism is better than mine above:

    the closure treats "this doc file is in scope" as "every symbol this doc
    file describes must be in scope too", even for components the ticket
    never touches

And their closing note is the cost: "Not actionable from here ... logged rather
than chased." That is the third independent party to reach the same verdict --
the finding is real, the fix is not available to the person hitting it, and the
only rational response is to record it and move on. A gate whose findings are
routinely and correctly ignored has stopped functioning as a gate.

THE MEASUREMENT SET IS NOW SIX, ACROSS TWO REPOSITORIES:

    ~140   this repo, from the SYS113 work
     345   this repo, a planner scoping a leaf to the gates catalog
      71   this repo, filing the ticket that became this one
     350+  this repo, the CLI parser package's anchors into two hub docs
     267   the consumer, one shared L5 design document
      10   the consumer, a smaller instance in the same family

Six independent hits, five different tasks, two codebases. Nobody set out to
study this rule; everyone tripped over it.

ONE POINT THEIR REPORT ADDS THAT MINE DID NOT, and it matters for the fix: the
document in question "documents the whole subsystem in one file BY DESIGN". So
the file shape the closure punishes is not an accident of authoring that could be
refactored away -- it is a deliberate, reasonable documentation structure. Any fix
premised on splitting hub documents would be asking every consumer to reorganise
their docs to suit a gate. That is the wrong direction, and it strengthens the
case for the diff-scoped option this ticket already prefers: narrow the closure to
the anchors the diff actually touches, which requires nothing of the document at
all.


## SF-18 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Recorded in scratchpad/STRATA-FRICTION.md as SF-18, evidence table row verbatim:

| SF-18 | Touching design/frob.strata detonates SCOPE002 over hundreds of unrelated doc anchors | tickets/T-4127/ticket.md: three agents independently measured 140, 345 and 71 on 2026-09-06; 88 open tickets mention SCOPE002 | every strata-touching ticket | MEDIUM |

And verbatim from the SF-18 section:
- this ticket's own body_changes record "three independent agents measured the
  same explosion at 140, 345 and 71 on 2026-09-06" and "9 open SCOPE002-titled
  tickets, 4 filed today by 3 different agents who each hit the explosion while
  working something unrelated". 88 ticket.md files under tickets/ mention
  SCOPE002.
- scratchpad/why-T-4111.txt:154-155: "Scope-closure WARN noise on
  design/frob.strata (500+ doc-anchor cross-references)".
- CHANGELOG T-3884 discloses it as known debt: "hundreds of unrelated symbols
  (docs/strata/roadmap.md alone describes 134), none of which this ticket touches".

FRESH MEASUREMENT, 2026-09-19, taken by the planner while filing epic T-4662:
filing the epic's own container ticket -- a ticket with an EMPTY scope that
touches no files at all -- emitted 587 scope-closure warnings, reported as
"579 more warning(s) collapsed -- set FROB_SCOPE_CLOSURE_VERBOSE=1 and retry to
see all 587". Every one named a design/frob.strata frob:doc anchor resolving into
docs/strata/roadmap.md or docs/guides/claude-hooks.md. The same 587 fired again
on T-4668, whose scope is three files, none of them design/frob.strata.

That is a fourth and fifth independent measurement, higher than any of the
original three, and it establishes something the earlier ones did not: the
explosion does not require TOUCHING design/frob.strata. It fires on a ticket
with no scope whatsoever. Whatever the fix is, "only tickets that touch the hub
file are affected" is not a true statement about the current behaviour.

NOW A CHILD OF T-4665 (story B of epic T-4662). Related by mechanism, not by
fix: T-4598 (KERNEL DECOUPLING epic) and T-4680 (DECISION: SF-10, split the
monofile) both reduce the same contention on design/frob.strata from other
directions.
