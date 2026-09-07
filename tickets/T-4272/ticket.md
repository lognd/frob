---
id: T-4272
title: 'multi-contributor epic claims: a remote collaborator claims an epic, everyone
  else sees it advisorily, and an abandoned claim expires without starving the ticket'
state: queued
kind: feature
origin: human
created: '2026-09-07'
priority: medium
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
no_scope_declared_reason: tier=epic design record; the implementation surface is not
  known until its leaves are cut, and the design deliberately spans the ticket store,
  the git ref layer, and the CLI rather than one module
body_changes:
- mode: append
  reason: 'owner decisions: the claim is the branch, claiming requires push access,
    an epic claim implies its leaves; and the stated purpose is work allocation for
    agents, not only mutual exclusion'
  actor: logan
  at: '2026-09-07'
  old_length: 5030
  new_length: 9282
- mode: append
  reason: 'owner decision settling the last open question: taking a leaf out of a
    claimed epic is permitted but is the one operation that requires a fresh remote
    read rather than the cached view'
  actor: logan
  at: '2026-09-07'
  old_length: 9282
  new_length: 12332
- mode: append
  reason: 'owner requirement: a remote claim must never hard-block local work; an
    explicit acknowledgement with a reason unblocks it and the contributor accepts
    ordinary merge conflicts as the consequence'
  actor: logan
  at: '2026-09-07'
  old_length: 12332
  new_length: 15527
- mode: append
  reason: 'records how claims should be modelled: as the existing ledger-ownership
    dimension re-keyed from worktree to branch, rather than as a new ticket state;
    corrects the premise that an addressed state form already exists'
  actor: logan
  at: '2026-09-07'
  old_length: 15527
  new_length: 19314
designated_repro_test: null
acceptance:
- text: given a claimed epic and a collaborator with no network access, when they
    run any frob verb, then nothing is refused and the claim view reports its own
    age rather than appearing empty
  evidence: []
- text: given a claim whose holder has produced no evidence of work for the configured
    duration, when another contributor claims it, then the claim transfers and the
    steal is recorded with the previous holder's last evidence
  evidence: []
- text: given two contributors claiming different epics at the same time, when both
    publish, then neither publish conflicts with the other and no shared record is
    rewritten
  evidence: []
- text: given a ticket whose scope overlaps a claimed epic's open leaves, when work
    on it is started, then the overlap is reported using the existing scope-collision
    machinery rather than a second implementation
  evidence: []
- text: given two agents on different machines asking for work at the same moment,
    when both attempt to take the same epic, then exactly one succeeds and the loser
    is told it lost before doing any work
  evidence: []
- text: given a claimed epic, when any contributor asks what is available, then the
    epic and its entire leaf subtree are excluded without a network call, using only
    the locally held ledger
  evidence: []
- text: given a stale claim, when another contributor takes it, then the takeover
    is recorded and the original branch is neither deleted nor rewritten
  evidence: []
- text: given contributors whose machine clocks disagree, when staleness is evaluated,
    then the verdict depends only on how long this repository has observed the tip
    unchanged and never on a timestamp written elsewhere
  evidence: []
- text: given a claimed epic, when a contributor takes one of its leaves, then a fresh
    remote read is performed first and the cached view is not accepted for this operation
  evidence: []
- text: given an unreachable remote, when a contributor tries to take a leaf out of
    a claimed epic, then that operation alone is refused while every other verb continues
    to work offline
  evidence: []
- text: given a leaf taken from a claimed epic, when the epic holder next refreshes,
    then they can see which leaf was taken and by whom, and the record names the epic
    tip staleness observed at the moment it was taken
  evidence: []
- text: given a claim held by someone else, when a contributor acknowledges the override
    with a reason, then the work proceeds locally and no verb is blocked, offline
    included
  evidence: []
- text: given an override, when it is attempted without a reason or as an ambient
    session-wide setting, then it is refused, since a reflex-supplied override makes
    the claim system decoration
  evidence: []
- text: given work done under an override, when it is landed, then the land output
    names whose claim was overridden and why, and the override record travels on the
    next push without the override itself having required the network
  evidence: []
- text: given a claimed ticket that its holder has started working, when its state
    and ownership are read, then both facts are representable at once and neither
    displaces the other
  evidence: []
- text: given the remote branch set and the ticket-side ownership view, when they
    disagree, then the branch set is authoritative and the ticket-side value is treated
    as a cached observation stamped with when it was taken
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MULTI-CONTRIBUTOR EPIC CLAIMS: LET A REMOTE COLLABORATOR CLAIM AN EPIC, LET
EVERYONE ELSE SEE IT, AND LET AN ABANDONED CLAIM EXPIRE. Owner request, scheduled
AFTER the alpha publish. This ticket is the design record; leaves come later.

THE CONSTRAINTS THE OWNER SET, WHICH ARE THE HARD PART. The check must not run on
every invocation, because that would put the network in the path of routine work.
It must never be load-bearing: frob works offline today and must keep working
offline, with no verb blocked by an unreachable remote. And an unworked claim must
not starve the ticket it holds.

THE CENTRAL OBSERVATION: THE LEDGER IS ALREADY DISTRIBUTED. Tickets live in git.
A claim does not need a server, a database, or an account system -- it needs a
place two people's repositories can both see. Git already provides one, and the
project already pushes and fetches it.

THE RECOMMENDED SHAPE: ONE REF PER CLAIM, NOT ONE FILE LISTING CLAIMS. Publish a
claim as its own ref under a dedicated namespace, named for the ticket it claims,
carrying the claimant, the claim time, the last heartbeat, and the intended
duration. One ref per ticket gives mutual exclusion for free: a claim is a
compare-and-swap push that fails if someone already holds it, and two people
claiming different epics never touch the same object, so there is nothing to
merge.

DO NOT IMPLEMENT THIS AS A SINGLE SHARED FILE OF ALL CLAIMS. This repository
already carries a defect of exactly that shape, where one record holds one entry
in a world that produces several, so the file names whichever writer went last and
a reader cannot tell a live entry from a finished one. A per-claim ref cannot
develop that failure.

LIVENESS MUST BE DEFINED BY WORK, NOT BY A HEARTBEAT ALONE. This project has
already been bitten by the opposite: a daemon polled faithfully for nineteen
hours while doing nothing useful, and any heartbeat-based check would have called
it healthy the whole time. A claim should be considered alive on evidence of
progress -- commits on the claimant's branch, a landed leaf, a ticket transition
-- and a bare periodic refresh should not by itself hold an epic indefinitely.
Expect to combine the two: a heartbeat proves the person still exists, evidence of
work proves the claim is still doing something.

EXPIRY MUST BE OBSERVABLE AND STEALING MUST BE AUDITABLE. When a claim goes
stale, anyone may take it, and taking it should be recorded rather than silent:
who took it, when, and what the previous claim's last evidence was. A silent steal
turns a coordination tool into a source of surprise merges.

THE NETWORK RULES, STATED AS REQUIREMENTS RATHER THAN INTENTIONS.
  Refresh opportunistically, on verbs where the person is already coordinating --
  starting work, landing, asking what is available -- and never on the checking
  path.
  Bound every remote call by a short timeout and fall back to the cached view
  without complaint.
  Cache the last fetched view with the time it was fetched.
  DISPLAY THAT AGE. An empty claim set because nobody has claimed anything and an
  empty claim set because the network was unreachable must never look identical.
  That is this project's dominant defect class and it would be inexcusable to
  introduce a fresh instance of it here.
  Never refuse a verb because a claim could not be fetched.

WHAT A CLAIM SHOULD DO WHEN IT IS SEEN. Advisory pressure, escalating with how
much the action costs to undo. Starting work on a claimed epic, or on a ticket
whose scope overlaps a claimed epic's open leaves, warns and asks for an explicit
acknowledgement that records why. Landing is the point where firmness is
reasonable, because landing already requires the network. Reading, checking, and
searching are never affected.

REUSE, DO NOT REBUILD. The overlap computation already exists: filing a ticket
already reports which other tickets' scopes it collides with. An epic's claimed
surface is the union of its open leaves' scopes, which makes the file-level
question a reuse of that same machinery rather than a new one. The existing
worktree-keyed lease layer stays exactly as it is and must NOT be conflated with
this: a lease is mutual exclusion inside one checkout, a claim is coordination
between people, and they answer different questions on different timescales.

OPEN QUESTIONS TO SETTLE BEFORE BUILDING.
  Whether a claim requires push access to the main repository, which decides
  whether outside contributors can claim at all or only collaborators can.
  How clock skew between contributors is handled, since expiry compares
  timestamps written on different machines; prefer generous durations and
  commit-based evidence over precise wall-clock arithmetic.
  Whether an epic claim implies its leaves are claimed, or whether leaves are
  claimed individually, and what happens when a second person wants one leaf of a
  claimed epic.
  What the view looks like for someone who has never fetched: the honest answer
  is "unknown", and the design must have a word for that state.



OWNER DECISIONS, RECORDED. These settle three of the four open questions and
change the recommended shape, so read them as superseding the design above where
they conflict.

  A claim BELONGS TO THE BRANCH the person is working on. The branch is the
  claim; there is no separate claim object to keep in sync with it.
  Claiming REQUIRES PUSH ACCESS. This is a collaborator feature, not an
  anonymous-contributor feature.
  An EPIC CLAIM IMPLIES ITS LEAVES. Claiming the parent claims the subtree.

AND THE PURPOSE, WHICH IS BIGGER THAN MUTUAL EXCLUSION. The goal is not only that
two people avoid overwriting each other -- version control already fails loudly
when they do. The goal is that each contributor's AGENTS KNOW WHAT TO WORK ON
without asking a person. This is a work-allocation problem wearing a locking
problem's clothes, and the allocation half is the harder and more valuable half.

WHAT BRANCH-AS-CLAIM BUYS, AND IT IS A LOT.

  Atomicity comes free. Creating a branch that does not exist is a
  compare-and-swap against the remote: two people racing to claim the same epic,
  one push succeeds and one is rejected. No lock, no negotiation, no server.

  Liveness stops needing a heartbeat entirely. A branch tip only moves when
  someone commits, so the tip IS the evidence of work, and it cannot be faked by
  a process that is merely running. This is exactly the property the daemon
  incident showed a heartbeat does not have.

  The remote payload shrinks to almost nothing. Because the ledger is already
  distributed and an epic claim implies its leaves, the remote only has to answer
  "which epics are claimed and what is each tip". Expanding a claimed epic into
  its subtree, and that subtree into a file surface, is local, offline, and
  already implemented.

MEASURE STALENESS BY LOCAL OBSERVATION, NOT BY REMOTE TIMESTAMPS. Do not compare
a commit date written on someone else's machine against this machine's clock;
that is the clock-skew problem the earlier draft flagged, and it is avoidable
rather than manageable. Instead record, locally, when this repository FIRST
OBSERVED a given branch at a given tip. A claim is stale when the tip has not
changed for longer than the configured duration AS SEEN FROM HERE. Every
participant reaches the same verdict without trusting anyone's clock, and a
contributor who is working continuously is never at risk of being reclaimed.

THE ALLOCATION VERB IS THE POINT, AND IT MUST CLAIM BEFORE IT WORKS. There must
be a way for an agent to ask for the next thing it may work on AND take it in one
atomic step, retrying on a lost race. Answering "what is available" and then
separately taking it leaves a window in which two agents both believe they won,
and they discover the collision only after doing the work -- which is precisely
the overwriting the owner wants to make very hard. The verb that answers the
question must be the verb that takes the claim.

RECLAIM WITHOUT DESTROYING. A stale claim must be takeable, but taking it must
never delete or rewrite the other person's branch. The new claimant publishes
their own branch and records the takeover, naming the tip they observed as stale
and for how long. The abandoned branch is left alone. Deleting a colleague's work
to reclaim a ticket would be a far worse failure than the starvation it fixes.

WHAT STILL PROTECTS AGAINST OVERWRITING, BECAUSE CLAIMS ALONE DO NOT. Claims
prevent two people from starting the same work. They do not prevent two people
whose disjoint claims touch the same file from colliding at land time. Keep the
existing land-time compare-and-swap against the integration branch and the
existing scope-overlap reporting; a claim system that quietly replaced them would
trade a loud failure for a silent one.

THE REMAINING OPEN QUESTION. What a second person does when they want ONE leaf of
a claimed epic. The owner's rule makes the whole subtree claimed, which is the
right default for avoiding surprise, but the escape hatch matters: either the
holder can release a leaf explicitly, or the requester can take it with an
acknowledgement that both parties can see. Decide this before building, because
retrofitting a partial release into a subtree claim is much harder than designing
for it.



THE LAST OPEN QUESTION IS SETTLED: TAKING A LEAF OUT OF A CLAIMED EPIC IS
ALLOWED, BUT IT IS THE ONE OPERATION THAT MUST ASK THE REMOTE FIRST.

THE RULE. A claimed epic covers its whole subtree, so its leaves are simply
absent from the available set every other contributor and agent computes. That
answer is derived locally from the cached view and costs nothing. Taking one of
those leaves anyway is an explicit act, and it requires a FRESH read of the
remote before it may proceed -- not the cached view, however recent.

WHY THE ASYMMETRY IS THE RIGHT SHAPE, AND NOT AN INCONSISTENCY. The default
assumption behind an epic claim is that a person is already working somewhere
inside it. Acting against that assumption is exactly the case where stale
information is most likely to cause the collision the whole system exists to
prevent. So the cheap, common, offline path stays cheap, common and offline, and
the rare contentious path pays a network round trip. Cost is placed where the
risk is, rather than spread evenly over every invocation.

WHAT THE FRESH READ IS ACTUALLY FOR, WHICH IS MORE THAN CONFIRMING THE CLAIM
STILL EXISTS. It answers whether the epic is being worked RIGHT NOW. A holder
whose branch tip advanced minutes ago is mid-flight and taking a leaf from under
them is very likely a collision. A holder whose tip has not moved in a long time
may have stopped, and taking a leaf is close to free. Those are different
situations that deserve different friction, and only a current read can tell them
apart. Use the same locally-observed staleness measure defined above rather than
comparing timestamps across machines.

OFFLINE MUST DEGRADE TOWARD NOT TAKING. If the remote cannot be reached, this
one operation is refused. Every other verb keeps working offline exactly as
before, and nothing about the ordinary path becomes network-dependent. State the
principle plainly so it survives future changes: when information is
unavailable, the system fails toward NOT taking someone else's work, never
toward taking it. An unreachable remote must never read as an absent claim.

THE TAKING IS ITSELF A CLAIM, WHICH MAKES THE COORDINATION SYMMETRIC. Since a
claim is a branch, taking a leaf means publishing a branch for that leaf. The
epic's holder sees it on their next refresh, their own agents then exclude that
leaf from their available set for the same reason everyone else excludes claimed
work, and no messaging channel is needed for either party to learn what happened.
The claim view should make this legible from both directions: a holder must be
able to see that a leaf inside their epic is held by someone else, and by whom.

RECORD THE OVERRIDE, INCLUDING WHAT WAS OBSERVED. When a leaf is taken from a
claimed epic, record who took it, who held the epic, and the epic tip's observed
staleness at that moment. That last part is what makes a later disagreement
resolvable: the taker can show the epic looked cold, or the record shows it did
not and the taker proceeded anyway. Both are useful; a bare "taken" is not.



THE ESCAPE VALVE: A REMOTE CLAIM MUST NEVER HARD-BLOCK WORK ON YOUR OWN MACHINE.
Owner requirement. Someone else's claim is information, not permission. A
contributor who decides to edit claimed files anyway must be able to, provided
they say so explicitly, and the consequence they accept is ordinary merge
conflicts.

THIS IS WHY THE FEATURE IS SAFE TO BUILD AT ALL. Version control already fails
loudly when two people change the same lines, and it fails at the moment the
change is integrated rather than at the moment it is written. The claim layer
exists to stop people from WASTING work, not to stop them from DOING it. Once
that is understood, an escape valve is not a weakening of the design; it is what
keeps the design from becoming a lock that can strand a contributor behind an
absent colleague.

DISTINGUISH THE ESCAPE VALVE FROM TAKING A LEAF, BECAUSE THEY ARE DIFFERENT ACTS.
Taking a leaf out of a claimed epic is CLAIMING: ownership transfers, a branch is
published, and it requires a fresh remote read. The escape valve is working
ANYWAY WITHOUT CLAIMING: nothing transfers, no ownership is asserted, and the
holder keeps the claim. The second must not silently perform the first.

WHAT EXPLICIT HAS TO MEAN, OR THE VALVE BECOMES THE DEFAULT. This project has a
name for gates whose cheapest clearing action degrades the record, and a
one-character flag that unblocks an agent is exactly that: it will be pasted into
every command in every script within a week, and the claim system will then be
decoration. So:

  The acknowledgement carries a REASON in the contributor's own words, and the
  operation is refused without one. A reason cannot be supplied by reflex.
  It is scoped to the specific claim being overridden, not a blanket setting.
  It expires, rather than persisting for the life of a checkout.
  It must NOT be settable once as ambient configuration or an environment
  variable that a session inherits. A per-session switch is indistinguishable
  from turning the feature off, and it would be turned on once and never
  reconsidered.

RECORD IT LOCALLY, PUBLISH IT OPPORTUNISTICALLY. The valve has to work offline,
so the record is written locally at the moment of the override. On the next push,
that record travels, and the claim holder can see that someone worked over their
claim, when, and why. Overriding is then socially visible rather than silent,
without making the override itself depend on the network. Do not require a
network round trip here; that would defeat the valve's purpose in the exact
situation it exists for.

SURFACE IT AT LAND TIME, WHERE A HUMAN IS ALREADY LOOKING. When work done under
an override is landed, the land output should say so plainly and name whose claim
was overridden. That is the moment the information is most useful and least
avoidable, and it costs nothing because landing already requires the network.

WHAT THE VALVE DOES NOT DO. It does not suppress the conflict, resolve it, or
promise the resulting merge will be clean. The contributor is accepting the
conflicts, not being spared them. It also does not release the holder's claim,
shorten its expiry, or mark the ticket as being worked by the overrider.



HOW CLAIMS SHOULD BE MODELLED IN THE TICKET SYSTEM: AS AN OWNERSHIP DIMENSION
ADDRESSED TO A BRANCH, NOT AS A NEW STATE.

A CORRECTION TO THE PREMISE FIRST, BECAUSE IT CHANGES THE COST BUT NOT THE
DIRECTION. There is no addressed state form in the model today. The state field
holds one of six plain values and carries no address; the actor who performed a
transition is recorded on the transition record, not on the ticket as a live
owner. So an addressed state is a new mechanism rather than an extension of an
existing one.

BUT THE OWNERSHIP CONCEPT DOES ALREADY EXIST, AND IT IS THE RIGHT FOUNDATION.
Ledger ownership is real and enforced today: a ticket leased to one worktree may
be WRITTEN only from that worktree, and any other worktree -- the shared primary
checkout included -- must refuse rather than clobber the holder's in-flight edit.
That rule exists because of a measured incident in which a field change written
from the primary checkout was dropped by a later merge, because the primary
checkout edited a ticket a worktree owned.

That is precisely the problem the owner wants solved between PEOPLE, already
solved between WORKTREES. The distributed feature is therefore not a new concept
bolted on; it is the existing ownership dimension re-keyed from a local worktree
to a branch that may live on someone else's machine.

WHY AN OWNERSHIP FIELD BEATS A NEW STATE, CONCRETELY.

  State and ownership are orthogonal, and collapsing them destroys information. A
  claimed ticket may be untouched, or actively worked, or blocked. If `claimed`
  is a state, what is the state of a claimed ticket someone has started? Either
  the claim is lost or the progress is, and the answer to that question is the
  thing every other contributor's agent needs in order to decide what to do.

  The state field is a state machine with defined transitions and terminal
  states. Ownership is not a stage of work; it comes and goes independently, can
  expire on its own, and can be overridden without any transition occurring. Rules
  written for one are wrong for the other.

  A second representation of one fact is this project's most repeated defect
  shape. Ownership already has a home; adding a state that means the same thing
  guarantees the two will disagree, and then a person has to decide which is
  lying.

THE ADDRESS IS THE BRANCH, WHICH THE OWNER ALREADY DECIDED. An ownership entry
names the branch that holds the claim, which in turn identifies the person, since
claiming requires push access. Recording the branch rather than a human name also
means liveness is readable from the same value: the branch tip is the evidence of
work, so the address and the heartbeat are one field rather than two that can
disagree.

THE FIELD MUST BE DERIVED, NOT AUTHORED. This is the constraint that keeps the
design honest. The truth about who holds a claim is the set of branches on the
remote, because that is what compare-and-swap makes atomic. The ticket-side
ownership entry is a CACHED VIEW of that truth, refreshed on the verbs that
already coordinate, and stamped with when it was observed. It must never become a
field a person edits and commits to the integration branch: that would serialize
every claim through the one branch this design deliberately avoids touching, and
it would create a record that can contradict the branches it describes.

WHAT THIS BUYS THE QUEUE. Availability becomes one predicate rather than a
special case. The verb that answers what an agent may work on already filters on
state, dependencies and leases; remote ownership joins that list as another
filter, expanded through the epic-implies-leaves rule, and everything downstream
-- the overlap reporting, the starvation checks, the board -- reads it without
learning a new vocabulary.
