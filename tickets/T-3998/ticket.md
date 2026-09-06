---
id: T-3998
title: 'F-212: a finished worktree''s lease can only be broken by stealing the whole
  ticket; there is no release verb'
state: queued
kind: ux
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
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'F-260 is the degenerate case of this ticket''s lifecycle gap: a lease with
    no worktree or agent at all, held over 40 files indefinitely and reported as Active
    by doable. Adds the three-state distinction our own fleet proved necessary --
    holder-gone-with-unlanded-commits must not be pruned as stale'
  actor: logan
  at: '2026-09-06'
  old_length: 3491
  new_length: 6616
- mode: set
  reason: 'F-263 contradicts the F-260 note I appended earlier: start did NOT collide
    with the same lease doable lists as active. The direct observation supersedes
    the generalisation, and the contradiction reveals a deeper defect -- two readers
    of lease state with different definitions, which must be reconciled before adding
    release/prune verbs'
  actor: logan
  at: '2026-09-06'
  old_length: 6616
  new_length: 9458
- mode: set
  reason: 'DOC006 fails CI on BOTH ubuntu and macOS against this ticket''s own prose:
    I quoted the consumer''s PROPOSED lease-prune verb in backticked command form,
    which parses as a live CLI invocation pointer and does not resolve because the
    subcommand does not exist. Rewritten as prose -- third time my own ticket text
    has broken the build this way'
  actor: logan
  at: '2026-09-06'
  old_length: 9458
  new_length: 9696
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-212, 2026-09-06:

  "Adding wasm-engine/build.rs to T-0181's scope from the sub-17-rust worktree
   failed with TicketOwnershipViolation because the lease sat with the sibling
   t-0181-shell worktree (finished, but never released). frob ticket scope
   offers no --steal-equivalent of its own; the only way forward was
   frob ticket start --steal on the ticket as a whole, which invalidates the
   other worktree's ability to close/land it."

THE DEFECT IS THAT THE ONLY AVAILABLE REMEDY IS DESTRUCTIVE AND OVER-BROAD. To
perform a small additive operation -- add one path to scope -- the user had to
seize the WHOLE ticket, revoking a sibling worktree's ability to close or land.
It happened to be safe there because that worktree was finished, but the user had
to determine that themselves, and nothing in the tool would have stopped them if
it had not been.

A CAPABILITY GAP, NOT A POLICY DISAGREEMENT: THERE IS NO RELEASE VERB. A lease is
acquired implicitly by `ticket start` and released implicitly by landing. A
worktree that finishes WITHOUT landing -- merged by hand, superseded, abandoned,
or simply done in sequence before a sibling branch continues -- holds its lease
forever, and the only way to break it is to steal the entire ticket. The
consumer's own suggested remedy is the right shape: `frob ticket release
<worktree>` once that worktree's work is merged.

NOTE THE SPECIFIC SHAPE THAT MAKES THIS COMMON RATHER THAN EXOTIC: two branches
sharing ONE ticket IN SEQUENCE. That is a normal workflow (do the shell half,
then the rust half), and it is exactly the case with no non-destructive path
today.

RELATED BUT DISTINCT -- do not merge these:
  - T-3949 / T-3927 are about lease GRANULARITY (whole-file leases serialising
    disjoint edits). This ticket is about lease LIFECYCLE (no way to release
    one). T-3927 already records that the lease has no lifecycle independent of
    ticket state; this is that gap, reported from the field.
  - T-3983 is about a stale worktree capturing ledger WRITES via cwd. Same
    underlying condition -- worktrees outliving their usefulness -- different
    symptom. A release verb would reduce both populations.

WHAT TO DETERMINE FIRST: is the implicit acquire/release pair deliberate? An
explicit release verb introduces a way to release a lease while work is still
live, which is a new footgun. So the release must be SAFE BY CONSTRUCTION, not
merely available: refuse (or loudly warn) when the worktree still has uncommitted
or unlanded work, and say what it found. A release that can silently strand
in-flight work would be worse than today's steal.

PREFER A RELEASE VERB OVER A SCOPE-ONLY STEAL. The consumer offers both. A
scope-only steal still takes something from another holder; a release is the
holder relinquishing. Where the holder is a finished worktree, release is the
honest operation and needs no adjudication of who deserves the lease.

MUST-FIRE FIXTURE: releasing a lease held by a worktree with unlanded work is
refused, naming what it found.
MUST-STAY-QUIET: releasing a lease held by a finished, merged worktree succeeds,
and a sibling worktree can then add scope without stealing the ticket.
THIRD FIXTURE: after release, the original worktree cannot silently continue to
act as the owner.

ACCEPTANCE
- A release path that does not revoke a sibling's ability to close or land.
- Refusal (not just a warning) when the holder still has live work.
- All three fixtures committed.
## F-260: THE OTHER HALF OF THE MISSING LIFECYCLE -- A LEASE WITH NO HOLDER AT ALL

logand.app-v2, 2026-09-06:

  "T-0088 is `in-progress` on main WITH A LEASE OVER 40 ENGINE FILES, but NO
   WORKTREE OR AGENT EXISTS for it (its work was merged into sub-17-rust in an
   earlier session and the ticket was never closed). `frob ticket doable` prints
   it under 'Active leases' AS IF LIVE, and every new engine ticket collides with
   it and needs `--steal`."

THIS TICKET records that a FINISHED worktree's lease can only be broken by
stealing the whole ticket. F-260 is the degenerate case: THERE IS NO WORKTREE AT
ALL, and the lease still holds -- over forty files, indefinitely, blocking every
future ticket in that area. So the lifecycle gap is not merely "release is
awkward"; a lease can outlive its holder entirely and nothing reclaims it.

THE AGGRAVATING DETAIL IS THAT WE REPORT IT AS LIVE. `doable` lists it under
"Active leases", so the one surface an operator consults to decide what can be
worked ASSERTS the lease is real. That is the third thing today that `doable`
reports wrongly or omits:
  - it offers tickets whose scope collides with a live lease (T-3949 / F-246),
  - it does not list stale ledger-holding processes (T-4048 / F-247),
  - and it presents a holder-less lease as active (this).
Each was reported separately; together they say `doable`'s model of "what can be
worked now" is incomplete in a consistent direction -- it knows about tickets and
dependencies but not about the RUNTIME state that actually blocks work. Worth
saying so explicitly wherever this gets fixed.

CONFIRMED IN THIS REPO TOO, so it is not consumer-specific: this session's own
fleet_status showed T-3936, T-3940, T-3947 and T-3799 as "in-progress with no
live lease", and I nearly treated one of them as a reclaimable stale lease when
it was in fact carrying UNLANDED WORK on a surviving branch. That is the hazard
in the opposite direction and it is why the fix must distinguish three states,
not two:
  (a) holder gone AND no unlanded work        -> genuinely stale, safe to prune
  (b) holder gone BUT the branch has commits  -> NOT stale; work is stranded and
                                                 pruning the lease hides it
  (c) holder alive                             -> live
The consumer's ask ("a lease whose worktree path no longer exists should be
reported as STALE and not block start") is correct for (a) and DANGEROUS for (b).
Detecting (b) is cheap -- `git log --oneline main..<branch>` -- and must be part
of this.

THEIR PROPOSED LEASE-PRUNE VERB IS THE RIGHT SHAPE (named in prose here, not
as a literal command invocation: no such subcommand exists yet, so writing it
in backticked command form parses as a live CLI pointer and DOC006 correctly
refuses it -- the same trap that broke CI from T-3931 and T-3976), with that
three-state check behind it, and it pairs naturally with the release verb this
ticket already asks for: release is the holder relinquishing deliberately, prune
is reclaiming after the holder is provably gone.

ADDITIONAL ACCEPTANCE
- A lease whose worktree no longer exists is distinguished into stale-safe vs
  work-stranded, never collapsed into one "stale" verdict.
- `doable` stops presenting a holder-less lease as active.
- Pruning refuses (loudly) when the branch still carries unlanded commits.

## F-263 CONTRADICTS F-260, AND THE CONTRADICTION IS THE FINDING

The F-260 note above records that T-0088's holder-less lease "blocks every new
engine ticket, which needs --steal". The SAME CONSUMER reported the opposite a
short time later:

  "`frob ticket start T-0236` did NOT collide with T-0088's lease on
   SpinningShape.tsx even though `frob ticket doable` lists T-0088 as an active
   lease over that file (F-260). So the 'ACTIVE LEASES' LISTING AND THE
   START-TIME COLLISION CHECK DISAGREE ABOUT WHAT A LEASE IS."

TAKE THE SECOND REPORT AS THE MORE RELIABLE ONE: it is a direct observation of a
`start` that succeeded, whereas the "blocks every new ticket" phrasing in F-260
was a generalisation. I appended F-260 at face value; this corrects it, and the
corrected picture is MORE interesting, not less.

TWO READERS OF LEASE STATE DISAGREE. `doable` presents T-0088 as holding an
active lease over SpinningShape.tsx; `start` looks at the same ticket and the
same file and finds no collision. So there is no single answer to "is this file
leased" -- there are at least two implementations with different notions of what
makes a lease live, and they are visibly out of step on a real case.

THAT REFRAMES THIS TICKET'S FIX. The earlier analysis assumed the problem was a
MISSING LIFECYCLE (no release verb, nothing reclaims a dead holder). That is
still true, but it is downstream of something simpler: THERE IS NO SHARED
DEFINITION OF A LIVE LEASE. Adding `release` and `prune` to a system where two
readers already disagree would give us a third opinion. So establish the
definition first:
  - What does `doable` consider a live lease, and from what state?
  - What does `start`'s collision check consider one, and from what state?
  - Which is right, and why does the other exist?
Then make both consume it. This is the same producer/validator desync shape
filed three times today (T-4042 collector vs binder, T-4020 doc anchor vs
runtime message, T-4043 formatter vs gate) -- one concept, two implementations,
users caught in between.

NOTE THE SAFETY IMPLICATION, which is why this outranks the ergonomics: if
`start` is the LENIENT reader, then two agents can hold overlapping scopes while
`doable` shows only one as active. That is a silent concurrency hazard, and it
is the opposite failure from the one F-260 complained about. Determine which
reader is permissive before deciding which to align to -- aligning `start` UP to
`doable`'s view would fix a hazard; aligning `doable` DOWN to `start`'s view
would entrench it.

ADDITIONAL ACCEPTANCE
- One definition of a live lease, consumed by both `doable` and `start`'s
  collision check -- verified by a fixture that asserts the two agree on the
  same file.
- Which reader was permissive, stated, with the concurrency implication
  addressed rather than assumed benign.
