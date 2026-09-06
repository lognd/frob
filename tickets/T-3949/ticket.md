---
id: T-3949
title: 'F-187: symbol-level scope satisfies AFFECT/COV/PRE but not SCOPE001, so whole-file
  leases still serialise disjoint edits'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: T-3927
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'F-246 adds a measured cost (one ~50k-token dispatch producing nothing but
    a description of the blockage) and a chain instance, plus a separable cheaper
    ask: frob ticket doable already knows both sides and should not offer a ticket
    whose scope collides with a live lease'
  actor: logan
  at: '2026-09-06'
  old_length: 3778
  new_length: 6583
- mode: set
  reason: 'F-259 is the most severe instance yet: a directory-glob lease on a shared
    test folder left a ticket with no compliant route, so it closed with an outstanding
    SCOPE001. Directory globs are a distinct aggravator from whole-file leases and
    scale their blast radius with the tree, not the work'
  actor: logan
  at: '2026-09-06'
  old_length: 6583
  new_length: 9721
- mode: set
  reason: F-288 shows frob ALREADY prints HOT FILE for the contended L5 doc in doable
    and does nothing with it -- a detector with no consumer, which is cheaper to fix
    than general granularity. It also names COMP-xxxx rows as an existing structural
    lease unit, matching F-246's frob:describes anchor observation
  actor: logan
  at: '2026-09-06'
  old_length: 9721
  new_length: 11676
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-187, plus an unnumbered 2026-09-06 report of the same
shape. This is now the FIFTH report of one problem from this consumer -- they
name F-127 and F-145 as the same theme, and it recurs across sessions and agents.
It is their single most-reported friction.

THE ASK, in their words: "Either SCOPE001 should honour symbol-level scope, or
leases should be symbol-level."

INSTANCE 1 (F-187). T-0173 needed ONE column in db/models/admin.py (leased by
T-0170) and ONE constructor argument in app/app.py (leased by T-0171).
`frob ticket scope --add admin.py::AdminAlert` WAS ACCEPTED and cleared the
closure gates -- AFFECT, COV and PRE were all satisfied by the symbol-level
scope. But SCOPE001 still demanded the literal FILE, the whole-file lease
refused it, and the ticket blocked itself on T-0170 and filed T-0177 purely to
finish later.

INSTANCE 2 (unnumbered, same day). T-0176 could not amend its OWN row in
docs/spec/L5-component-design/SUB-03-db.md: ScopeLeaseConflict, held by
in-progress T-0173. T-0173's declared scope per its dispatch brief was
notifications/app.py/models/admin.py -- not that doc at all; the lease was on a
whole-file glob whose actual edits never touched the row T-0176 needed. T-0176
shipped WITHOUT the amendment.

WHAT MAKES THIS A DESIGN DEFECT RATHER THAN FRICTION. Symbol-level scope is
ALREADY ACCEPTED and ALREADY SUFFICIENT for three of the four gates that consume
scope. SCOPE001 and the lease are the two that ignore it. So the system offers a
precision it then refuses to honour -- the user does the right thing, is told it
worked, and is blocked anyway. That is worse than not supporting symbol scope at
all, because it wastes the user's correct action.

IT ALSO CAPS PARALLELISM DIRECTLY, which is the expensive part. Two tickets with
provably disjoint edits inside one file cannot proceed concurrently. The
consumer's remedy in both instances was to serialise and file a follow-up ticket
-- so the defect manufactures queue entries.

THIS IS THE SCOPE-CONFLATION EPIC (T-3927) MEASURED IN THE FIELD. Scope is a
write lease AND an evidence-coverage declaration in one field; these two reports
are what that conflation costs. Treat this ticket as T-3927's motivating
evidence, and check T-3927 before designing -- do not re-derive the analysis.

DETERMINE FIRST, BEFORE CHOOSING A FIX: why does SCOPE001 demand the literal
file when AFFECT/COV/PRE do not? If that is deliberate (a soundness requirement
-- e.g. it cannot prove a symbol-level edge without the whole file), then the
answer is symbol-level LEASES, not symbol-level SCOPE001, and the ask resolves
the other way. If it is merely an unexamined file-granularity assumption, honour
the symbol scope. DO NOT GUESS BETWEEN THESE -- the two fixes have opposite
shapes and the consumer explicitly offered both.

THE CHEAP HALF, worth doing regardless of which fix wins: their second report
asks for "at least a way to SEE which glob T-0173 actually leased so a human can
judge overlap before it blocks." The refusal message today names the holder but
not the glob that actually collided. That is a message change, it is
independently useful, and it does not wait on the design decision.

MUST-FIRE FIXTURE: two tickets whose symbol-level scopes genuinely OVERLAP still
conflict.
MUST-STAY-QUIET: two tickets with disjoint symbol-level scopes in the SAME FILE
both proceed. This is the fixture that proves the ticket.
THIRD FIXTURE: the refusal message names the specific colliding glob.

ACCEPTANCE
- The SCOPE001 file-granularity question answered (deliberate or unexamined),
  with the reason, before any fix is chosen.
- Disjoint symbol-level edits in one file no longer serialise.
- The refusal names the colliding glob.
- All three fixtures committed.
## F-246: A MEASURED COST, AND A SECOND ASK THAT IS CHEAPER THAN THE MAIN FIX

logand.app-v2, 2026-09-06. Same defect, now on a DOCS file and with a price tag:

  "T-0089 could not start because T-0226 (a licence doc anchor, A TWO-LINE
   ADDITION) holds a whole-file lease on
   docs/spec/L5-component-design/SUB-16-public-pages.md, and T-0226 was itself
   queued behind T-0218's lease on frontend/scripts/licenses.ts. An agent slot
   was burned filing a draft ticket that describes the chain and then exiting.
   Cost: ONE DISPATCH (~50k tokens, 84s) WITH ZERO OUTPUT; the coordinator had to
   re-order the queue by hand."

This is the first report to QUANTIFY the cost, and it is the strongest evidence
on this ticket. A two-line documentation addition fenced off an entire L5 spec
file, which fenced off an unrelated ticket, which consumed a full agent dispatch
that produced nothing but a description of the blockage. Note also the CHAIN --
T-0089 behind T-0226 behind T-0218 -- so lease granularity does not just
serialise pairs, it composes into queues.

THEIR SECOND SUGGESTION IS SEPARABLE AND SHIPPABLE BEFORE THE GRANULARITY FIX,
and I want it treated as its own child rather than folded in:

  "`frob ticket doable` should already exclude tickets whose declared scope
   collides with a LIVE lease (IT KNOWS BOTH SIDES), or mark them 'doable after
   T-0226'."

They are right that both sides are known. `doable` is the verb whose entire job
is answering "what can be worked now", and it is currently answering a question
nobody asked -- what is unblocked by DEPENDENCIES -- while ignoring the other
thing that makes a ticket unworkable. That is why an agent slot was spent: the
dispatch was made on `doable`'s word. Fixing this does not require deciding
anything about lease granularity, and it converts a burned dispatch into a
correct queue ordering. IT ALSO FIXES THE COORDINATOR-SIDE COST directly -- I
have been picking dispatch sets by hand all session.

THEIR FIRST SUGGESTION, section-granular doc leases, is the docs-shaped version
of this ticket's symbol-granular ask, with a useful concrete unit: "the
frob:describes anchor table is already a unit". So for documentation there may be
an existing structural boundary to lease against, rather than needing a new
concept. Worth checking before designing anything general.

ADDITIONAL ACCEPTANCE
- `frob ticket doable` excludes (or explicitly annotates) tickets whose declared
  scope collides with a live lease. Shippable independently of granularity.
- Whether the frob:describes anchor table can serve as the doc-lease unit,
  answered before designing a new one.

ADDITIONAL FIXTURE: a ticket whose scope collides with a live lease does not
appear as plainly doable -- so no dispatch can be made on a ticket that cannot
start.

## F-259: A TICKET CLOSED WITH AN OUTSTANDING VIOLATION BECAUSE THE RULE LEFT NO OTHER ROUTE

logand.app-v2, 2026-09-06:

  "T-0191 (scope: ImageCarousel.tsx) had to edit
   frontend/tests/unit/pages/projects.test.tsx (the UT row for its comp), but
   `frob ticket scope --add` was REFUSED because T-0092 holds a live lease on the
   whole glob frontend/tests/unit/pages/. THE TEST EDIT STILL HAD TO HAPPEN
   (test-first), so T-0191 CLOSED WITH AN OUTSTANDING SCOPE001."

THIS IS THE WORST OUTCOME THIS DEFECT HAS PRODUCED. The previous reports cost
serialisation, a wasted dispatch, and manual queue re-ordering. This one produced
a TICKET CLOSED IN KNOWN VIOLATION -- the enforcement system's own record now
contains a ticket that admits it broke a rule, because the rule offered no
compliant path.

THE SQUEEZE IS STRUCTURAL, not a judgement call by the agent:
  - TDD001 and the test-first workflow REQUIRE the test edit.
  - The file is inside a DIRECTORY-GLOB lease held by a sibling ticket.
  - `scope --add` is refused, so the edit cannot be declared.
  - Not editing means not doing the work.
Every available action violates something. The agent picked the option that
delivered the work and left an honest violation on the record, which is the least
bad choice and should not be held against it.

DIRECTORY-GLOB LEASES ARE THE SPECIFIC AGGRAVATOR HERE, and they deserve separate
treatment from the whole-FILE leases the earlier reports describe. A lease on
`frontend/tests/unit/pages/` fences off every test file for every component in
that tree -- so ONE ticket touching one page's tests blocks EVERY sibling
component ticket, because shared test directories are exactly where unrelated
work co-locates. The blast radius scales with the directory, not with the work.

THEIR TWO SUGGESTIONS, and the second is the cheaper one to reason about:
  1. LEASE THE CONCRETE FILES A TICKET'S UT ROWS NAME, rather than the directory
     glob the scope was written with. This is the symbol/section-granularity ask
     from the earlier reports, applied to directories: derive the lease from what
     the ticket actually declares it will touch.
  2. LET `--add` SUCCEED FOR A FILE THE LEASEHOLDER HAS NOT TOUCHED. Narrower and
     testable against real state -- the leaseholder's own diff is knowable, so a
     file it has not modified is provably uncontended. NOTE this needs care: "has
     not touched YET" is not "will not touch", so it trades a hard refusal for a
     possible later conflict. Say which risk is preferred rather than assuming.

CROSS-REFERENCE T-4050 (the scope-denominator epic): this is the LEASE side, not
the denominator side, and the two must not be conflated -- but a ticket that
cannot declare a file it must edit will produce denominator findings forever,
because its declared scope can never match its real diff. The two subsystems
produce each other's symptoms.

ADDITIONAL ACCEPTANCE
- A ticket that must edit a file inside a sibling's directory-glob lease has a
  compliant route -- it never has to close in known violation.
- Directory-glob leases specifically addressed, not just whole-file ones.

## F-288: FROB ITSELF ALREADY PRINTS "HOT FILE" AND STILL CANNOT ACT ON IT

logand.app-v2, 2026-09-06:

  "one L5 doc is the HOT FILE of every shell ticket; whole-file leases serialise
   the whole branch ... `frob ticket doable` EVEN PRINTS 'HOT FILE' ... lease L5
   docs at row/anchor granularity (COMP-xxxx rows are the natural unit)."

THE MOST TELLING DETAIL IS THAT WE ALREADY DETECT IT. `frob ticket doable`
identifies the file as HOT -- it knows this one file is contended by many tickets
-- and then offers no mechanism that uses that knowledge. The information exists,
is computed, is displayed, and changes nothing. Every ticket in that area still
serialises behind a whole-file lease.

So this is not a missing detector. It is a detector whose output has no consumer,
which is a different and cheaper problem to fix than the general granularity
question: something that already knows a file is contended could, at minimum,
warn at `start` that taking this lease will block N other tickets, or order the
queue to take the hot file first, or refuse to hand it out for a two-line edit.

THEIR PROPOSED UNIT IS CONCRETE AND ALREADY EXISTS IN THE DATA: "COMP-xxxx rows
are the natural unit". This is the same observation F-246 made about the
`frob:describes` anchor table -- for these L5 docs there is ALREADY a structural
sub-file boundary, so row/anchor-granular leasing does not require inventing a
concept, only leasing against a unit the documents already have. That materially
lowers the cost of the docs half of this ticket, and it should be attempted
before the general symbol-granularity work.

ADDITIONAL ACCEPTANCE
- `doable`'s existing HOT FILE detection is wired to something -- at minimum a
  warning at `start` naming how many tickets the lease will block.
- Row/anchor-granular leasing for L5 docs evaluated against the COMP-xxxx row
  boundary that already exists, separately from (and before) general
  symbol-granular leasing.
