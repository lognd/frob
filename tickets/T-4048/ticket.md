---
id: T-4048
title: 'F-247: a ledger mutation hung for 2h after its own ticket landed, never writing
  and never exiting (second occurrence)'
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
- src/frob/tickets/_scope.py
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
Consumer logand.app-v2 F-247, 2026-09-06, SECOND OCCURRENCE:

  "`frob ticket scope T-0211 --add design/vmodel.strata` was still alive 7050 s
   later, long after T-0211 was landed on main by the coordinator. Same shape as
   the orphaned `frob ticket scope T-0031` pair earlier (killed by pid). No lock
   file was reported but THE PROCESS NEVER EXITS AND NEVER WRITES."

TWO HOURS. Not slow -- HUNG. And the distinguishing detail is that it never
writes: this is not a long computation nearing completion, it is a process that
will never finish and never produce its effect.

THIS IS PROBABLY THE ROOT OF A CHAIN I HAVE ALREADY FILED THREE TICKETS AGAINST,
and if so those become symptoms:

    F-247 (this)  an orphaned ledger process hangs forever holding the lock
        -> T-3993 ledger verbs "run for minutes in silence"  ... they are not
           running, they are WAITING on a lock a dead-but-alive process holds
        -> agents and harnesses cannot tell hung from slow, so they KILL them
           (the consumer killed three; I killed two `ticket new` calls myself)
        -> T-4022 a killed verb leaves its partial write, producing duplicate
           acceptance criteria
        -> T-4035/T-4041 territory: manual cleanup, hand-edited ledger state

VERIFY THAT CAUSAL CHAIN RATHER THAN ASSUMING IT. It is a hypothesis of mine, not
a measured fact, and I have been wrong about exactly this kind of plausible chain
twice today. The specific question: are the multi-minute `ticket new` /
`scope --add` times reported in T-3993 LOCK WAITS behind an orphan, or genuine
computation? The consumer's own note that "no lock file was reported" argues the
mechanism may NOT be the land lock at all -- so establish what the hung process
is actually blocked on (`py-spy dump`, or PYTHONFAULTHANDLER=1 with a SIGABRT,
which this repo has used before to dump a stuck process's stack in one command)
BEFORE building a timeout around it.

THEIR TWO SUGGESTIONS, both good, and the first is the safety net regardless of
root cause:

  1. A HARD WALL-CLOCK BUDGET ON LEDGER MUTATIONS, failing with a message rather
     than hanging. They note the rapid sweep already has one, so there is a
     precedent and probably reusable machinery. A verb that cannot finish must
     SAY SO -- an operation that hangs forever is the worst possible outcome
     because it is the one the caller cannot act on.
     CAREFUL: a timeout interacts directly with T-4022 (a killed mutation leaves
     a partial write). A budget that aborts mid-write reproduces that corruption
     on a schedule instead of by accident. So the budget must abort ATOMICALLY --
     these two tickets must be designed together, and T-4022 should probably land
     first.
  2. `frob ticket doable` COULD LIST STALE LEDGER-HOLDING PROCESSES the way it
     lists active leases. Cheap, diagnostic, and it turns an invisible condition
     into a visible one. Note this is the second thing today that doable should
     surface and does not (T-3949: it should also exclude tickets colliding with
     a live lease) -- worth asking whether doable's job is "what can be worked"
     in general, rather than a fixed set of checks.

WHAT MAKES THIS URGENT BEYOND THE HANG: the process outlived its own ticket. The
work was landed on main by a coordinator while the orphan was still running, so
it held resources for a completed unit of work with no owner watching. Whatever
the fix, a ledger mutation for a ticket that has reached a terminal state should
not still be running.

MUST-FIRE FIXTURE: a ledger mutation that cannot complete within its budget fails
with a message naming the verb and what it was waiting on.
MUST-STAY-QUIET: a normal ledger mutation on a busy repo still completes -- the
budget must not turn a slow success into a failure. Pick the number from measured
timings, not intuition.
THIRD FIXTURE: an aborted-on-budget mutation leaves the ledger byte-identical to
before (the T-4022 interaction, made checkable).

ACCEPTANCE
- What the hung process is actually blocked on, established by a stack dump
  rather than inferred.
- Whether the T-3993 slowness is this, answered rather than assumed.
- A wall-clock budget that aborts atomically, designed with T-4022.
- All three fixtures committed.