---
id: T-4121
title: scope closure is file-granular over multi-anchor doc tables, so a one-row edit
  demands every symbol in the file and consumers revert correct doc fixes instead
state: queued
kind: bug
origin: agent
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
- src/frob/app/ticket_runner/_new.py
- src/frob/gates/_tickets_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: 'the two homes of the closure: _new.py computes and reports scope closure
    at filing time (the only module naming it), and _tickets_gate.py carries the SCOPE001
    enforcement the consumer hit via check --only scope. The diff-scoped option this
    ticket asks to evaluate first would land in one or both'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'the two homes of the closure: _new.py computes and reports scope closure
    at filing time (the only module naming it), and _tickets_gate.py carries the SCOPE001
    enforcement the consumer hit via check --only scope. The diff-scoped option this
    ticket asks to evaluate first would land in one or both'
  actor: logan
  at: '2026-09-06'
body_changes:
- mode: set
  reason: 'records the measurement taken while filing: this repo''s own shared gate-rule
    catalog reproduces the consumer''s defect at 71 and 345 closure warnings in two
    independent measurements the same day, and we have been working around it by hand
    exactly as they did'
  actor: logan
  at: '2026-09-06'
  old_length: 3725
  new_length: 4943
designated_repro_test: null
acceptance:
- text: given a doc file carrying anchors for many symbols, when a ticket edits one
    row, then only that row's symbol is required in scope
  evidence: []
- text: given a doc edit that genuinely spans several symbols' sections, when scope
    closure runs, then all of them are still required
  evidence: []
- text: given a single-symbol doc file, when a ticket edits it, then behaviour is
    unchanged from today
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
EDITING ONE ROW OF A SHARED DOC TABLE PULLS EVERY SYMBOL ANCHORED ANYWHERE IN
THAT FILE INTO THE TICKET'S REQUIRED SCOPE. Reported as logand.app-v2 F-308: a
one-sentence edit to a single table row caused the scope gate to demand that
every symbol anchored anywhere in that document be in the ticket's scope. The
consumer REVERTED the correct edit rather than widen scope that far.

THAT REVERSION IS THE FINDING. A gate whose cheapest clearing action is to
abandon a correct documentation fix is the wrong-incentive class: the rule made
the record worse. And it does so specifically to the smallest, safest kind of doc
change -- a one-row correction -- which is the change we most want people to make
freely.

THE MECHANISM IS FILE-GRANULAR OWNERSHIP APPLIED TO A FILE THAT IS SHARED BY
CONSTRUCTION. Scope closure is right in general: if you edit the doc a symbol is
anchored to, you are implicitly touching that symbol's contract. It breaks down
for a doc file that is a TABLE OF MANY INDEPENDENT ROWS, each anchored to a
different symbol. There, file granularity asserts a coupling that does not exist
-- editing row 40 says nothing about row 3 -- so the closure computes a true
statement about the file and a false one about the change.

THE CONSUMER POINTS AT THEIR OWN EARLIER REPORT, which proposed row-granular doc
ownership, and observes it would fix BOTH this fan-out AND the lease collisions
they have reported separately on the same files. That is a strong signal: one
mechanism, two symptom families, reported independently. Neither of those reports
is in this queue yet, so this ticket carries both.

BEFORE DESIGNING ANYTHING, MEASURE THE POPULATION. Row-granular ownership is a
significant mechanism and it is only worth it if shared multi-anchor doc files
are common rather than one consumer's habit. Count, in this repo AND in the
consumer's: how many doc files carry anchors for more than one symbol, what the
distribution of anchors-per-file looks like, and how often a single-row edit
would trigger a fan-out of more than a handful of symbols. Report those numbers
BEFORE proposing a design. If the distribution is thin, a cheaper fix wins.

THE CHEAPER FIXES, TO BE RULED OUT EXPLICITLY RATHER THAN SKIPPED:
  - Narrow the closure to the anchors the DIFF ACTUALLY TOUCHES rather than every
    anchor in the file. This needs no new declaration syntax at all -- the diff
    already says which lines changed, and an anchor's position in the file is
    already known. If this works it is strictly better than new ownership syntax,
    because nothing has to be declared or maintained.
  - Treat a doc file as row-granular only when it declares itself so, leaving
    every existing file's behaviour unchanged.
Evaluate the diff-based option FIRST. It is the one that requires no consumer
action, and a fix consumers must adopt is a fix most of them will not get.

MUST-FIRE FIXTURE:   a one-row edit to a doc file carrying anchors for many
                     symbols requires only the edited row's symbol in scope.
MUST-STAY-QUIET:     an edit to a doc section that genuinely covers several
                     symbols still requires all of them -- the closure must not
                     become a blanket escape.
THIRD FIXTURE:       an edit to a single-symbol doc file behaves exactly as today.

ACCEPTANCE
- The anchors-per-doc-file distribution measured and reported for both repos
  before any design is chosen.
- The diff-scoped option evaluated first and either adopted or ruled out with a
  stated reason.
- The lease-collision symptom on the same files checked against the chosen fix --
  the consumer says one mechanism causes both; confirm or refute that.
- All three fixtures committed.

MEASURED IN THIS REPO WHILE FILING THIS TICKET, which settles the population
question the section above asks for on our side at least:

  - Scoping this very ticket to the two closure modules produced 71 closure
    warnings, of which the overwhelming majority name ONE file: the shared gates
    module catalog under docs/modules/. Every rule handler in the gate module
    anchors its doc into that one catalog, so touching any handler pulls the
    whole catalog in.
  - Earlier the same day, a planner decomposing an unrelated epic tried to scope
    a leaf to that same catalog and measured 345 closure warnings plus overlap
    with 8 unrelated queued tickets. It dropped the catalog from every leaf's
    scope and left the doc update as an unscoped append at close time.

SO WE HAVE THE CONSUMER'S DEFECT IN OUR OWN TREE, and we have already been
working around it by hand the way they did -- they reverted a correct edit, we
drop the doc from scope and patch it at close. Both workarounds degrade the
record. This is not a consumer-only problem and should not be scoped as one; the
gate module catalog is the exact shape F-308 describes, a table of many
independent rows each anchored to a different symbol.
