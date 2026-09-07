---
id: T-4180
title: the TypeScript test collector indexes nested agent worktrees, so evidence can
  bind to a node id that exists only on another branch
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_ts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a repository containing a nested worktree with its own tests, when the
    collector runs, then the cache contains no node id from that worktree
  evidence: []
- text: given the primary tree's own tests, when the collector runs, then they are
    still collected in full
  evidence: []
- text: given an unknown-evidence refusal, when it is printed, then it names the expected
    id shape and the nearest cached id
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE TYPESCRIPT TEST COLLECTOR WALKS INTO NESTED AGENT WORKTREES AND RECORDS THEIR
NODE IDS UNDER THE PRIMARY ROOT. Reported in logand.app-v2's correction to F-383,
after they retracted the original premise. Three findings came out of that
correction; this is the serious one.

    the PRIMARY checkout's cache indexed 271 files, including every
    .claude worktree frontend test path, so the collector walks into sibling
    worktrees and records their node ids under the primary root

CONSEQUENCE, IN THEIR WORDS AND MINE: evidence bound from that cache would cite a
path that DOES NOT EXIST ON MAIN. That is worse than the noise this class usually
produces. A gate scanning a nested worktree yields a false finding, which is
visible and annoying. A COLLECTOR doing it yields a durable, apparently-valid
EVIDENCE BINDING pointing at a test that only exists on someone else's branch --
recorded in the ledger, surviving that branch's deletion, and resolving to nothing
forever after.

THIS IS THE FOURTH INSTANCE OF NESTED-WORKTREE CONTAMINATION IN THIS DRIVE, and
the classes it has already produced are worth listing because they show the reach:
a consumer's type stage reporting unresolved imports for files on other branches
(they excluded the directory in three separate config files); a doc-pointer rule
reading agent scratch; six of our own self-scan tests failing locally while CI was
clean; and now a collector writing cross-branch node ids into an evidence cache.
frob CREATES those worktrees, so it knows where they are, and each surface has had
to learn that independently.

NOT REPRODUCIBLE IN THIS REPOSITORY, AND THE REASON MATTERS. I checked all four
collect caches here: the python cache holds 13657 ids with ZERO worktree paths,
and our TypeScript cache is empty because frob has no TypeScript tests. So our own
green proves nothing about this, and the fix cannot be fixture-tested from our
tree without a synthetic project. This is the dogfooding-blindness class again --
say so in the done report rather than discovering it during implementation.

The python collector's cleanliness is itself a useful clue: it is invoked with a
configured root and test paths, so it never wanders. Check whether the TypeScript
collector discovers files by walking instead, and if so, route it through the
shared pruned walk that already knows what a nested worktree is.

TWO SMALLER FINDINGS FROM THE SAME CORRECTION, both diagnostic, both cheap:

  1. NODE ID SHAPE IS NOT DISCOVERABLE FROM THE REFUSAL. Their vitest ids are of
     the form file, then describe block, then test name; their agent bound file
     plus test name without the describe segment and got a bare unknown-evidence
     refusal. The cache was RIGHT THERE and the message showed neither the
     expected shape nor the nearest cached id. This repo already does exactly that
     elsewhere -- the doc-anchor rule prints the anchors it found and the nearest
     match by edit distance. Copy that behaviour here.

  2. A STALE CACHE IS SILENT. One branch's cache predated the test it was being
     asked about by a day, and nothing said so; the id simply did not resolve.
     Warn when the cache is older than the file whose tests are being looked up.
     Note this is the same shape as an open ticket about the gate cache serving a
     stale result after the underlying file changed -- check whether one staleness
     mechanism can serve both rather than building a second.

MUST-FIRE FIXTURE:   a repository containing a nested worktree with its own tests
                     produces a collection cache containing no node id from that
                     worktree.
MUST-STAY-QUIET:     the primary tree's own tests are still collected in full.
THIRD FIXTURE:       an unknown-evidence refusal prints the expected id shape and
                     the nearest cached id.

ACCEPTANCE
- The collector excludes nested worktrees, ideally by reusing the existing
  nested-worktree helper rather than a new path pattern.
- The unknown-evidence refusal names the expected shape and nearest match.
- Cache staleness is reported rather than silent, reusing the existing staleness
  mechanism if one fits.
- The un-fixturable-here limitation stated explicitly in the done report.
- All three fixtures committed.
