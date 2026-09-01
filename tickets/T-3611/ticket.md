---
id: T-3611
title: 'frob write-path latency: LandInProgress window starvation, land queue default,
  wait mode, guard false-positives'
state: queued
kind: ux
origin: human
created: '2026-08-31'
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
Epic: frob write-path latency and availability. The tool is correct but
operationally slow under fleet load; this epic tracks making it USABLE.

Measured 2026-08-31/09-01 (this session, 5-agent fleet):
- CLI startup is NOT the problem: `frob --version` 0.335s; a refused
  `ticket drop` returns in 0.6s (2ms internal).
- The problem is WINDOW STARVATION: filing verbs (new/drop/reconcile)
  refuse with LandInProgress whenever .frob/land.lock is held OR any
  live land process has cwd=root (T-1619 belt-and-braces scan,
  _leases.py:2017). A land takes minutes in-band; with 5 agents landing
  back-to-back the no-land window essentially never opens: one
  coordinator drop of T-3212 was refused across ~15 attempts over ~3
  HOURS. Agents hand-roll 60s sleep retry loops that mostly MISS the
  brief open windows between queued lands.
- Lands serialize on land.lock (correct) but each pays its full in-band
  cost inside the lock; queue depth x minutes = hours of wall time.
  Rapid/deferred verification IS on (quarantine clear) -- the in-band
  remainder (pre-land scoped gates, squash, splice, natives verify) is
  what everyone waits behind.
- Guard false-positives compound it (measured 2026-09-01, all in one
  session): (a) the root-write guard refuses `land --help` from the
  root -- a pure read; (b) the same guard refused a heredoc writing
  ticket-body text to /tmp because the BODY TEXT contained frob verb
  phrases -- a lexical match on command content; (c) the
  frob-timeout-guard hook blocked `land --help` run from a worktree as
  a "known stall pattern" -- pattern-matched the verb, not the argv.
  Fleet doctrine already says: token/grammar checks, never lexical.

Children (file each as its own ticket, blocked_by this epic id):
1. Narrow LandInProgress for tickets-dir-only writers (the big one).
2. Land queue/drain as the default agent path.
3. --wait mode on write verbs.
4. Guards: pass --help/--version/read-only forms unconditionally; stop
   matching command CONTENT (heredoc bodies) lexically.
