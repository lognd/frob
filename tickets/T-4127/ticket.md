---
id: T-4127
title: SCOPE002 explodes on hub files (design/frob.strata, docs/modules/gates.md)
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
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
