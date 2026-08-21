---
id: T-2359
title: Reformat the 138 files pending ruff-format as one deliberate commit, unblocking
  T-2244/T-2245
state: queued
kind: feature
origin: agent
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/diagnosis-nudge.py
- scripts/fleet_status.py
- src/frob/app/design_runner.py
- src/frob/app/profile_runner.py
- src/frob/app/pyfmt_runner.py
- src/frob/app/sys_runner.py
- src/frob/app/telemetry/__init__.py
- src/frob/app/telemetry/_footguns.py
- src/frob/app/telemetry/_usage.py
- src/frob/app/ticket_runner/_attach_backfill.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/app/worktree_runner.py
- src/frob/arch/_abstraction.py
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/diagnosis-nudge.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: scripts/fleet_status.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/design_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/profile_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/pyfmt_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/__init__.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/_footguns.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/telemetry/_usage.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_attach_backfill.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/worktree_runner.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/arch/_abstraction.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/check/_python.py
  reason: batch 1 of ruff-format-only reformat, re-measured 184 files current (ticket
    filed at stale 138); excludes T-2761/_2764/_2762 in-flight scope
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
acceptance:
- text: given the repo after this lands, when ruff format --check . runs, then zero
    files need reformatting
  evidence: []
- text: given the format-only commit, when its diff is reviewed, then it contains
    no semantic changes and no fixture-corpus files
  evidence: []
- text: given the test suite, when it runs after the reformat, then it passes unchanged
  evidence: []
threat: null
component: build
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17: `uv run ruff format --check .` reports
**138 files would be reformatted, 975 already formatted**.

This is a latent hazard, not cosmetic debt. T-1382's child T-2244 wants to
repoint the Makefile's `format:`/`lint-fix:` targets at a real write-mode
ruff pass. The moment that lands, the FIRST person or agent to run the
target rewrites 138 files in one go -- a repo-wide diff blast with no
owning ticket, landing on top of whatever else is in flight. An agent
measured this and correctly declined to land T-2244 for exactly that
reason, which is why T-2244 is still queued and T-2245 (docs + call-site
audit) is transitively blocked behind it.

The dependency chain is real and currently stalled:
    T-2245 (docs audit) blocked_by T-2244 (repoint targets)
    T-2244 held because running the repointed target detonates 138 files

THE FIX IS SEQUENCING, and it must happen in this order:
 1. THIS TICKET: reformat all 138 files as ONE deliberate, format-only
    commit. No logic changes, nothing else in the diff.
 2. THEN T-2244 becomes safe -- repointing a target that is already a
    no-op on a clean tree changes nothing for the next caller.
 3. THEN T-2245 can write docs describing a state that is actually true.

WHY THIS NEEDS A QUIET FLEET, and why I am filing rather than doing it:
a 138-file reformat conflicts with every in-flight worktree that touches
any of those files. With a multi-agent fleet running, that is a large
merge-conflict surface imposed on work already in progress. This should be
landed when few or no agents hold worktrees, as a single commit, not
opportunistically mid-drive.

EXECUTION NOTES:
 - Use a SCOPED formatter invocation, not `frob fmt .`. A broad-path `frob
   fmt` rewrote 49 unrelated `.strata` FIXTURE files earlier today (T-2298,
   now fixed to exclude test corpora by default) -- verify the fixture
   exclusion holds before trusting a bulk run.
 - `git status` and review the diff shape before committing: a format-only
   commit must contain zero semantic changes. Spot-check several files.
 - Re-run the full test suite after. Formatting is supposed to be
   behaviour-preserving; "supposed to be" is not evidence.

POSITIVE CONTROLS: (1) `ruff format --check .` reports zero files needing
reformat afterward; (2) the test suite passes unchanged; (3) no `.strata`
or other fixture corpus file appears in the diff.
