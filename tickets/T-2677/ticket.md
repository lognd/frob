---
id: T-2677
title: fleet_status.py's REPO constant resolves via __file__, giving 0 live leases
  when run from a worktree
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: test coverage for the REPO-resolution fix lives in this file
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: frob:doc target for the REPO constant this ticket changes
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_positive_control_matches_primary_checkout
- tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_falls_back_when_not_a_git_checkout
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestResolveRepoRoot::test_positive_control_matches_primary_checkout
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
scripts/fleet_status.py's module-level constants (REPO, LEASES,
TICKETS_DIR, WORKTREES, VERIFY_QUEUE, VERIFY_WATERMARK, QUARANTINE) are
all derived from `Path(__file__).resolve().parent.parent` -- the
location of the RUNNING SCRIPT's own file, not the coordinator's actual
working directory or the shared primary checkout.

Because every worktree under .claude/worktrees/<name>/ has its own copy
of scripts/fleet_status.py (it is a tracked file, checked out into
every worktree same as any other source file), running
`python scripts/fleet_status.py` from inside a worktree resolves REPO
to that worktree's own root -- and `.git` there is a FILE (a gitdir
pointer to `.git/worktrees/<name>`), not a directory, so
`LEASES = REPO / ".git" / "frob-leases"` silently resolves to a path
that can never exist.

Measured directly (T-2665's own investigation, 2026-08-19): running
`uv run python scripts/fleet_status.py` from inside
.claude/worktrees/t-2665 reported

    LEASES 5 (0 live, 5 leaked, 0 blocked-open)
      T-1686 -> <no worktree>  [LEAK]
      T-2570 -> <no worktree>  [LEAK]
      T-2665 -> <no worktree>  [LEAK]
      T-2666 -> <no worktree>  [LEAK]
      T-draft-64ebeb12 -> <no worktree>  [LEAK]

for tickets that were all genuinely live (including T-2665's own
worktree, actively being worked in at that exact moment). Running the
identical command from the primary checkout (/home/logan/projects/frob)
immediately afterward correctly reported all five as `live`. This is
strictly more dangerous than T-2665's own original report (a false LEAK
for one ticket) -- an agent or coordinator who happens to invoke
fleet_status.py from inside a worktree (an easy mistake: it is a
tracked, runnable script sitting right there in the checkout) sees
EVERY in-progress ticket flagged [LEAK] simultaneously, which is exactly
the shape that would make a `frob ticket requeue` sweep look justified
fleet-wide.

Suggested fix direction (not investigated in depth -- this ticket is a
finding, not a design): resolve these constants against the actual git
common-dir (`git rev-parse --git-common-dir`, the same primitive
frob.gitio already uses elsewhere in this repo for exactly this
worktree-vs-common-dir distinction) rather than `__file__`'s location,
or at minimum detect the worktree-vs-primary-checkout case and warn
loudly rather than silently reporting an empty lease set as "0 live".

Positive control for a fix: fleet_status.py invoked from inside ANY
worktree must report the same LEASES section as when invoked from the
primary checkout, for the same real fleet state.