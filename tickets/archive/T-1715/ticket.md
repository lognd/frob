---
id: T-1715
title: frob ticket land --finish deletes the calling agent's own worktree cwd, stranding
  it with no recovery
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_leases.py
- tests/unit/test_land_finish_guard.py
- docs/modules/tickets.md
- src/frob/_cli_parsers/_ticket/_progress.py
- frob.lock
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: need to wire --force onto `ticket land` so --finish can be overridden for
    a genuinely wedged tree per T-1715 plan
  actor: logan
  at: '2026-08-07'
- op: add
  glob: frob.lock
  reason: frob ack src/frob/tickets/_leases.py::sweep_worktrees (DRIFT001 self-heal
    after this ticket edited sweep_worktrees) writes frob.lock as a byproduct
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface auto-writes this derived interface manifest whenever
    a tickets_ledger public symbol changes (WorktreeInUseError/refuse_if_worktree_in_use/scan_for_live_worktree_process)
    -- land absorbs this automatically per playbook sec 0 item 5, adding to scope
    for a clean pre-land check
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_none_when_no_process_matches
- tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree::test_finds_a_live_lease_pinned_to_the_worktree
- tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree::test_expired_lease_is_not_live
- tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_refuses_on_a_live_process_and_names_the_pid
- tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_refuses_on_a_live_lease
- tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse::test_allows_when_neither_signal_fires
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_removes_a_worktree_with_no_live_process
- tests/unit/test_land_finish_guard.py::TestFinishWorktree::test_force_removes_despite_a_live_process
- tests/unit/test_land_finish_guard.py::TestForceFlagParsing::test_force_flag_sets_the_namespace_dest
- tests/unit/test_land_finish_guard.py::TestForceFlagParsing::test_force_defaults_false
designated_repro_test: null
threat: null
component: null
---
`frob ticket land --finish` removed the worktree that the calling agent
was still using as its process working directory, stranding it: every
subsequent tool call failed with "the isolation worktree appears to have
been removed", and the agent could not create a replacement (worktree
creation is reserved to whatever spawned it). It had to be abandoned and
re-dispatched, losing its accumulated context.

Observed 2026-08-06 landing T-1683. The land itself was correct and
`LAND-PROOF` verified; `--finish` then did exactly what its contract says
and removed the finished worktree. Nothing malfunctioned. The hazard is
that the command has no idea the directory it is deleting is a live
process's cwd.

This is a footgun specifically because the agent was following
instructions: dispatch briefs tell agents to run `frob ticket land` FROM
THE ROOT CHECKOUT targeting `--worktree <their own>`. So the natural,
documented invocation is the one that deletes the caller's own sandbox
out from under it.

Fix: refuse `--finish` when the target worktree is in use, and say why.

The detection machinery already exists -- do not write a second copy.
`frob.tickets._leases` has `_proc_cwd` and `_scan_for_live_land_process`
from T-1619's belt-and-braces process scan, which already answers "is
some live process sitting in this directory". Reuse it:

- If any live process has the target worktree as its cwd, refuse with a
  message naming the pid and the fact that removal would strand it, and
  point at landing WITHOUT `--finish` plus a later `frob worktree sweep`.
- If the worktree holds an active lease, same refusal.
- `--force` may override, since a genuinely orphaned worktree whose
  holder died still needs removing, and the process scan cannot always
  prove a pid is dead.

Related but separate, and worth doing in the same pass because it is the
same "the tool assumed something about who is calling it" family: the
refusal message should also work when the caller IS the stranded process
-- i.e. deleting your own cwd -- since that is the common case here.

Regression coverage: a worktree with a live process cwd'd into it is
refused by `--finish`; the same worktree with no live process is removed;
`--force` removes it either way. Assert the refusal names the pid --
"could not finish" without naming what is holding it repeats the
DirtyMain lesson (T-1698/T-1699) where an error that did not name its own
cause cost three agents their budgets.