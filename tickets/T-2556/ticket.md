---
id: T-2556
title: worktree-lease pre-commit hook refuses agent commits inside the leased worktree,
  and its error message advises a remedy that does not work
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/project.py
evidence_scope:
- tests/test_scaffold_worktree_lease_hook.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_inside_leased_worktree_is_allowed
- tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_against_shared_root_is_still_refused
- tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_refusal_names_a_remedy_that_actually_works
- tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_in_a_worktree_other_than_the_leased_one_is_refused
- tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_coordinator_commit_unaffected_in_both_locations
- tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_land_internal_commit_in_root_is_exempt
designated_repro_test: tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware::test_commit_inside_leased_worktree_is_allowed
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18. The worktree-lease pre-commit hook (template in
`src/frob/scaffold/project.py:387-394`, installed by
`frob scaffold apply`, T-0431) refuses on
FROB_AGENT UNCONDITIONALLY:

    if [ -n "$FROB_AGENT" ]; then
        echo "frob: refusing commit -- FROB_AGENT=$FROB_AGENT is set" >&2
        echo "frob: an agent-context shell must not commit directly in $(pwd)" >&2
        echo "frob: unset FROB_AGENT if deliberate, or run from the leased worktree" >&2
        exit 1
    fi

TWO DEFECTS, one of them user-facing-wrong.

1. THE GUARD IS OVER-BROAD. It never checks WHERE the commit is
   happening. The incident it guards against (T-0431) is an agent
   committing against the SHARED ROOT instead of its own worktree -- but
   a commit inside the correctly-leased worktree is refused identically.
   `frob ticket land`'s own internal pre-land wip commit therefore cannot
   run in the environment the playbook instructs every dispatched agent
   to set. An agent hit this today: land attempt refused with
   "refusing commit -- FROB_AGENT=1 is set in this shell", and only
   succeeded after setting FROB_WORKTREE and UNSETTING FROB_AGENT.

2. THE ERROR MESSAGE GIVES ADVICE THAT DOES NOT WORK. It says
   "or run from the leased worktree". Running from the leased worktree
   does not help, because the guard does not look at the path. Anyone
   following the printed instruction fails again identically. That is
   worse than no advice.

WHY IT IS INTERMITTENT, which is why it survived this long: it only
fires when the tree is dirty enough that `land` needs a wip commit. Most
lands never reach that path, so this presents as a random land failure
rather than a reproducible one.

DELIVERABLE: make the refusal conditional on the commit actually
happening OUTSIDE the leased worktree. The hook already has the
information it needs -- `git rev-parse --show-toplevel` versus the
worktree registry, or FROB_WORKTREE when set. Keep the T-0431 protection
intact: an agent-context commit against the SHARED ROOT must still be
refused. Only the in-worktree case becomes allowed.

Fix the TEMPLATE in `src/frob/scaffold/project.py`, not the installed
`.git/hooks/pre-commit` -- the installed copy is materialized from it,
and editing the copy leaves every other repo (and every reinstall) still
broken. This repo has already been bitten by editing a materialized copy
instead of its source.

Also fix the message so it names the actual remedy.

POSITIVE CONTROLS, BOTH DIRECTIONS, MANDATORY:
- an agent-context commit against the SHARED ROOT must still be REFUSED
  (this is the whole point of T-0431 and must not regress);
- an agent-context commit inside the correctly-leased worktree must be
  ALLOWED;
- a coordinator commit (FROB_AGENT unset) must be unaffected in both
  locations.

Note the second control is the one that would have caught this: the
existing test suite presumably only exercises the refusal, which is why
an unconditional guard passed review. A guard needs a must-NOT-fire case
as much as a must-fire one.