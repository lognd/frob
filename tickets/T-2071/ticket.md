---
id: T-2071
title: 'Agent-context root-write guard is inert: FROB_AGENT is unset in dispatched
  agent shells'
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/project.py
- tests/test_scaffold_worktree_lease_hook.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/project.py
  reason: 'fact-based root-write guard: hook body keys off checkout identity + staged
    non-ledger files, not FROB_AGENT'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: 'fact-based root-write guard: hook body keys off checkout identity + staged
    non-ledger files, not FROB_AGENT'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent
- tests/unit/test_coordinator_scripts.py::TestRootDirt::test_dirty_repo
designated_repro_test: tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent
acceptance:
- text: given a shell with FROB_AGENT unset (as every dispatched agent has), when
    it writes and commits a source file in the shared repo root, then the write is
    refused or surfaced as agent-context root contamination -- this test MUST fail
    against current main
  evidence:
  - tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent
- text: given the fleet is running, when scripts/fleet_status.py probes ROOT, then
    a dirty root reports the offending paths rather than a bare dirty/clean verdict
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRootDirt::test_dirty_repo
acceptance_amendments:
- op: remove
  index: 1
  old_text: given an agent has dirtied the shared root, when another agent's land
    is DirtyMain-refused, then the refusal names the offending path AND identifies
    it as foreign to the landing ticket, so the operator can route it without hand-diagnosis
  new_text: null
  reason: src/frob/tickets/_land.py was held by T-2105's LIVE cross-worktree lease
    for T-2071's entire duration, so the DirtyMain-refusal-names-the-owning-ticket
    improvement could not be implemented here; split out as a follow-up ticket (T-2118)
    to be worked once the lease frees. Criteria 1 and 3 (renumbered to 2) remain in
    T-2071 and are both evidenced.
  actor: logan
  at: '2026-08-11'
threat: null
component: tickets
labels:
- fleet-blocking
- guard
anchor: false
anchor_reason: null
land_commit: null
---
## Measured evidence

`FROB_AGENT` is UNSET in every shell spawned by the Agent tool. Measured
directly from a dispatched agent's shell:

    echo "FROB_AGENT is: [${FROB_AGENT:-UNSET}]"
    FROB_AGENT is: [UNSET]

`.git/hooks/pre-commit` (installed by `frob scaffold
install-worktree-lease-hook`, T-0431) opens with:

    if [ -n "$FROB_AGENT" ]; then
        echo "frob: refusing commit -- FROB_AGENT=$FROB_AGENT is set in this shell"
        echo "frob: an agent-context shell must not commit directly in $(pwd)"

So the guard whose entire purpose is "an agent-context shell must not commit
directly in the root" never fires for the population it exists to stop. It is
inert, not merely late.

## Observed consequences, same hour, three separate agents

Two agents in ONE dispatch wave edited the shared root instead of a worktree:

    git -C /home/logan/projects/frob status --porcelain
     M src/frob/app/ticket_runner/_query.py         # agent A
     M src/frob/testing/_coverage_refresh.py        # agent B

1. Agent B's uncommitted file DirtyMain-refused a THIRD agent's
   `frob ticket land T-1226`. Finished, gate-clean work could not reach main
   because of an unrelated agent's working-tree edit.

2. Agent A's edit was half-applied when `frob ticket doable` ran from the
   root:

       ERROR: main: unhandled exception during dispatch:
       name 'NamedTuple' is not defined

   The class had been added before its import. The queue command that drives
   the whole drain was broken repo-wide for the length of that window.
   `git show HEAD:src/frob/app/ticket_runner/_query.py | grep -c NamedTuple`
   returned 0, confirming main itself was never broken -- it was purely the
   root's dirty working tree being executed live.

3. Agent B then committed its fix directly onto main (`d59f1cc97`), as did
   two ticket-filing commits (`d3c862df7`, `b607d0b94`). The hook refused
   none of them.

## Why a per-cause patch is the wrong answer

This is the THIRD distinct mechanism producing the same failure class, each
fixed individually before:

  - T-2026: a killed `frob ticket new` retry loop left an untracked ticket dir
  - T-2034: `frob ticket doable` abandoned ledger writes on lock loss
  - this ticket: an agent edits/commits the root directly

When one class recurs through three unrelated causes, the per-cause patch is
not the fix.

## DO NOT FIX IT THIS WAY

- **Do not add a line to the agent brief or the playbook.** Both agents here
  were already briefed to use a worktree and both were pointed at the
  playbook's worktree warm-up. A brief that warns about a trap is not a fix --
  four agents were explicitly warned about the confirmatory-only-evidence trap
  and all four still fell in, because the tooling gave them no way to detect
  it. If a written rule was not followed, the rule is not the fix.
- **Do not simply export `FROB_AGENT` from the dispatch path and call it
  done.** That makes the existing hook fire, but the hook guards COMMIT time,
  and DirtyMain blocking begins at EDIT time -- consequences (1) and (2) above
  both happened with nothing committed. Setting the variable is likely
  necessary but is not sufficient, and shipping only that would leave the
  fleet-blocking window fully open while looking fixed.
- **Do not weaken or special-case DirtyMain** to tolerate foreign dirt. The
  refusal is correct; it is what surfaced this at all.

## Direction (the implementer decides, but weigh these)

Prefer a guard that makes the hazard impossible or self-healing at the moment
it starts, over one that reports it later:

  (a) detect a dirty root caused by a non-root actor and surface it where the
      operator already looks -- `scripts/fleet_status.py` already probes ROOT;
      a land refusal should name the OWNING agent and file, not just refuse;
  (b) have the dispatch path place agents in a worktree by construction, so
      editing the root is not reachable rather than merely discouraged;
  (c) if a commit-time refusal is kept, make its trigger a fact about WHERE
      the shell is (root vs. worktree) rather than an env var the dispatcher
      may or may not set -- a guard keyed on a variable nobody sets is
      indistinguishable from no guard.

Note the standing preference for automatic behaviour and surfacing over new
commands: a command requires knowing the command.

## First test must fail

The first acceptance test must FAIL against current main -- i.e. it must
demonstrate that today, with `FROB_AGENT` unset, an agent-context write to the
shared root is accepted with no refusal and no surfacing.

## Done report

Changed:
- src/frob/scaffold/project.py::_WORKTREE_LEASE_HOOK_SCRIPT (added a second, FROB_AGENT-independent guard)
- src/frob/scaffold/project.py::install_worktree_lease_hook (docstring updated to describe the new guard)

Evidence:
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent (--accepts 1, designated repro: FAILED_AT_PARENT at e5780d953, confirmed with --check-repro)
- tests/test_scaffold_worktree_lease_hook.py full class: 16 passed (was 15; +1 new test, 0 regressions)
- criterion 3 (fleet_status.py names offending paths on a dirty root) already holds on main, unchanged by this ticket: tests/unit/test_coordinator_scripts.py::TestRootDirt::test_dirty_repo, 2 passed -- fleet_status.root_dirt()/main() already return/print per-path porcelain lines, not a bare verdict.

Filed:
- T-2119 (docs): document the new guard in docs/commands/scaffold.md#public-api once T-1382's live lease on docs/commands/** frees (out of T-2071's own scope; AFFECT001 waived with this reason)
- T-2118 (bug): criterion 2's remaining gap -- _log_dirty_main_refusal (src/frob/tickets/_land.py) should name the OWNING ticket when dirt belongs to some OTHER open ticket's scope, not just distinguish "no open ticket" from generic; could not be done under T-2071 because src/frob/tickets/_land.py was held by T-2105's live cross-worktree lease for T-2071's entire duration.

Gates: frob check --ticket T-2071 clean except:
  - gate:SCOPE SCOPE001 on tickets/T-2119/ticket.md -- pre-existing gap: the SCOPE001 cross-ticket exemption's ticket-ref regex (_TICKET_REF_RE = T-\d{4}) does not match a draft id's commit subject, so filing a residue ticket from inside another ticket's worktree always trips this; not caused by this ticket's own diff content, not fixed here (regex touch would be its own out-of-scope change to src/frob/gates/__init__.py).
  - gate:TICK TICK004 (T-0969 rotting, 15d) -- pre-existing repo-wide backlog rot, unrelated to this ticket's files.
  - ruff-format (110 files repo-wide) -- pre-existing, unrelated to touched files (ruff-check on the touched files alone: All checks passed).
  gate:ARCH/gate:AFFECT/gate:PRE, all clean after fixes (ARCH001 line-count and AFFECT001 waiver, both addressed in this ticket's own diff).

### Changed
```
 src/frob/scaffold/project.py               | 86 ++++++++++++++++++++++++------
 tests/test_scaffold_worktree_lease_hook.py | 45 ++++++++++++++++
 tickets/T-2071/ticket.md                   | 25 +++++++--
 tickets/T-2118/ticket.md         | 24 +++++++++
 tickets/T-2119/ticket.md         | 23 ++++++++
 5 files changed, 184 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: TICK004@tickets.md
