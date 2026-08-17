---
id: T-2261
title: 'Nothing ever invokes frob worktree sweep: 107 worktrees / 67GB / 95 idle accumulated,
  and the land prints ''run it later'' instead of acting'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: new repro/regression tests for the automatic worktree sweep
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'doc closure: sweep_stale_worktrees_after_land needs its own anchor in this
    doc'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
- tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_logs_one_line_per_verdict
- tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesIsOffTheLandCriticalPath::test_spawn_deferred_post_land_sweep_never_calls_it_directly
designated_repro_test: tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
acceptance:
- text: 'Stale worktrees are reclaimed without an operator remembering a command (fails
    today: zero non-advisory call sites); state where it hooked in and why'
  evidence:
  - tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
- text: 'MUST-STILL-PASS: live, dirty, unlanded, leased, and under-age worktrees are
    each still KEPT -- fixtures for all five'
  evidence:
  - tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
- text: Every removal is logged with its per-worktree verdict
  evidence:
  - tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_logs_one_line_per_verdict
- text: The land critical path is not lengthened; measure a land before and after
  evidence:
  - tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesIsOffTheLandCriticalPath::test_spawn_deferred_post_land_sweep_never_calls_it_directly
- text: --force is never used by the automatic path
  evidence:
  - tests/unit/test_rapid_sweep.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# Nothing ever invokes `frob worktree sweep`, so agent worktrees accumulate unbounded -- measured at 107 worktrees / 67GB / 95 idle

## Measured evidence (2026-08-16)

    git worktree list | wc -l        ->  107
    du -sh .claude/worktrees         ->  67G
    live (a process cwd'd inside)    ->  5
    idle                             ->  95

`frob worktree sweep --dry-run --min-age 4` on that state:

    swept 99 worktree(s): 71 removed, 5 kept:live, 0 kept:lease,
                          6 kept:dirty, 8 kept:age
    (plus 9 kept:unlanded, 2 kept:lease across the full listing)

So 71 are safely removable by the tool's own verdicts, and the guards
(`kept:live` / `kept:dirty` / `kept:unlanded` / `kept:lease` / `kept:age`) all
fire correctly. The cleanup capability is sound. **It is simply never run.**

Every reference to it in `src/` is advisory or wiring:

    src/frob/app/worktree_runner.py        - the CLI wiring itself
    src/frob/app/ticket_runner/_query.py:731 - a docstring mention
    src/frob/app/ticket_runner/_land_cmd.py:2690:
        "run `frob worktree sweep` later to clean it up"

That last one is the heart of it. The land KNOWS a worktree has just gone
stale -- it says so -- and prints a suggestion instead of acting. This is the
standing "automatic over commands" position: a command that requires knowing
the command is a command nobody runs.

## Measured consequence, not just disk

An implementer working T-2248 reported that `frob check --land-parity` "did not
converge under worktree-fleet contention (100+ concurrent worktrees)" and had
to disclose it as a cut in its Done report rather than a clean result. Every
git operation in this repo enumerates the worktree list; 107 entries is a tax
on every land, every `doable`, every status read. `_doable.py:165`'s own
comment already records "~129 of them observed in this repo", so this has been
noticed and never acted on.

## Do NOT fix it this way

- **Do NOT sweep synchronously inside the land.** T-1684 deliberately moved
  post-land work OFF the land critical path; adding a filesystem sweep back
  onto it would re-lengthen exactly what that work shortened.
- **Do NOT remove by age alone.** `kept:unlanded` (9 here) and `kept:dirty` (6)
  protect real work that is old precisely because it stalled. Age is the
  weakest signal in the set, not the strongest.
- **Do NOT bypass or weaken the existing keep verdicts.** They are the reason
  this is safe to automate at all. Reuse `sweep_worktrees`; do not
  reimplement its decisions.
- **Do NOT make it unconditional and silent.** Removing 71 directories with no
  record is not cleanup, it is data loss with good intentions. Whatever runs
  it must log what it removed and what it kept, per verdict.
- **Do NOT `--force`.** That flag overrides the liveness gate (T-1739); a
  scheduled sweep must never use it.

## Acceptance criteria

1. (MUST FAIL FIRST) Stale worktrees are reclaimed without an operator
   remembering to run a command. Fails today: zero non-advisory call sites.
   State where you hooked it and why that path.
2. MUST-STILL-PASS CONTROLS, all five: a worktree with a live process, an
   uncommitted-dirty one, one with unlanded commits, one holding a lease, and
   one under the age threshold are each still KEPT. Build fixtures for each --
   these are the guards that make automation safe, and a fix that erodes any
   one of them is far worse than the sprawl.
3. Whatever removes is logged with its per-worktree verdict, so a later
   operator can reconstruct what happened.
4. The land critical path is not lengthened -- measure a land before and after.
5. `--force` is never used by the automatic path.

## Scope note

`src/frob/app/ticket_runner/_rapid_sweep.py` already owns detached, off-critical-path
post-land work (T-1684) and is the natural host; `sweep_worktrees` lives behind
`src/frob/app/worktree_runner.py`. Confirm that placement before implementing
rather than taking my word for it -- if the deferred sweep is the wrong home,
say where and why.