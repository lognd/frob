---
id: T-3927
title: 'scope conflates write-lease with evidence-coverage and the lease has no lifecycle:
  nine consumer findings, one design decision'
state: queued
kind: feature
origin: human
created: '2026-09-05'
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
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
SCOPE CONFLATES TWO THINGS IN ONE FIELD -- WHAT A TICKET MAY WRITE, AND WHAT
EVIDENCE COVERS IT -- AND THE WRITE LEASE HAS NO LIFECYCLE INDEPENDENT OF THE
TICKET'S STATE. Nine consumer findings across two repos reduce to that sentence.
This is a design ticket, not a bug fix.

THE EVIDENCE, all measured by consumers doing real work on 2026-09-05:

  STALE LEASES BLOCK LIVE WORK -- reported FOUR TIMES:
    F-127  long-lived leases from parked branches block every ticket touching
           shared files
    F-133  stale leases from never-closed tickets on a parked branch block
           every new ticket on that branch
    F-142  `frob ticket start` chain-blocked on NINE stale in-progress leases
           from ONE parked branch; the operator had to hand-scan with
           `grep -l '^state: in-progress'` to find them
    F-118  cross-worktree leases block a legitimately shared file for the whole
           life of the other ticket
  A four-time re-report is a prioritisation signal in itself: the queue is not
  draining what consumers actually hit.

  THE WORKAROUND DETONATES A CORRECT GUARD:
    F-141  requeuing those tickets to release their leases triggers
           TerminalStateRegression (T-1914), invalidating every PRE-EXISTING
           worktree's land. T-1914 is right -- a backward transition genuinely
           invalidates assumptions open worktrees made. The composition is the
           defect, not either piece.

  SHARED FILES CANNOT BE SHARED:
    F-085  a lease on a shared L5 doc forces WAIVERS instead of anchors, so the
           waiver records "deferred" for work that was merely lease-blocked --
           corrupting the waiver population F-082 wants to measure
    F-060  a genuinely repo-wide ticket needs broad scope, and broad scope
           blocks everyone; in practice it can never be worked while a fleet is
           busy
    threat-model item 7  a security pass could not get a clean lease because
           another ticket held the whole .strata file though its work never
           touched the added regions -- collision is FILE-granular, not
           section-granular

  AND PRECISE SCOPE IS TOO EXPENSIVE TO DECLARE, which is what pushes people to
  the over-broad scopes above:
    F-106  directory globs refused -- files must be listed individually
    F-063  `scope --add` takes ONE glob per flag -- one call per file
    F-051  each call takes 3-5 MINUTES under agent load
    F-138  the resulting shell loop stalls past the 120s tool timeout
  A fifteen-file ticket is close to an hour of scope declaration.

FIRST-HAND CORROBORATION FROM THIS REPO: I dispatched T-3844 without specifying
scope; it declared `tickets/**`, which is a write lease over every open ticket,
and DEADLOCKED T-3843 -- the CI blocker -- for an hour. I read that as my
briefing failure, and it was. But the tool made the sloppy path the cheap one.

WHAT TO DECIDE. Do not fix these one at a time; they will re-emerge as each
other. The candidate directions, each with a real cost:
  (a) SPLIT THE FIELD. Separate "files this ticket may write" from "files whose
      evidence covers it". Most of the shared-doc pain is a READ relationship
      being charged a WRITE price.
  (b) LEASE MODES. exclusive-write / shared-append / read-for-evidence, so a
      shared doc or a hub .strata can be held by several tickets in compatible
      modes.
  (c) A LEASE LIFECYCLE INDEPENDENT OF TICKET STATE -- so a parked branch's
      leases can be reclaimed without a backward transition. THIS IS THE
      NARROWEST FIX THAT ADDRESSES THE FOUR-TIME RE-REPORT, and it should be
      checked FIRST: frob already has `frob ticket sweep`, lease reclamation,
      and fleet_status classifies leases live/reclaimable/leaked. A supported
      release path may already exist and merely be undiscoverable -- the
      operator reached for requeue, which suggests it is not obvious. VERIFY
      BEFORE BUILDING.
  (d) MAKE PRECISE SCOPE CHEAP -- directory globs, repeatable flags, a fast
      path. This does not fix the semantics but removes the pressure that
      produces over-broad scopes.

DO NOT WEAKEN THE LEASE ITSELF. It is what stops two agents editing one file,
and this fleet has already been deadlocked by a dirty shared root. Every
direction above preserves exclusivity where it is genuinely needed.

MUST-FIRE FIXTURES:
  - two tickets that genuinely WRITE the same file still conflict
  - a backward ledger transition still invalidates worktrees cut before it
MUST-STAY-QUIET FIXTURES:
  - two tickets that merely CITE the same doc as evidence do not conflict
  - a parked branch's leases can be reclaimed without rewriting ticket state
  - declaring scope for a fifteen-file ticket takes one command

ACCEPTANCE
- The (c) check performed and reported FIRST: does a supported lease-release
  path already exist?
- A stated decision among (a)-(d), with the cost of the chosen one named.
- The nine consumer findings mapped to whichever are resolved and whichever
  remain.
- Both fixture sets committed.
