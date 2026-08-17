## Done report

### What `ticket work` prints now

Right after the worktree is created/reused and natives are built, before
`_start` runs (both `frob ticket work <id>` and `frob ticket work --cluster
<id>`), a new `_print_agent_env_hint` helper (`_lifecycle.py`) calls
`agent_env_exports(worktree)` -- the SAME function `frob agent env` itself
calls, never a second computation -- and logs (INFO, stdout):

    ticket work: T-2258 apply this worktree's agent env before running
    pytest/frob directly from your shell: eval "$(uv run frob agent env
    /home/logan/projects/frob/.claude/worktrees/t-2258)"

and, ONLY when `agent_env_exports` actually returned a
`PYTEST_XDIST_AUTO_NUM_WORKERS` value (another live lease exists), a second
line naming the bound:

    ticket work: T-2258 fleet context detected (another live lease exists)
    -- the eval above bounds PYTEST_XDIST_AUTO_NUM_WORKERS=6

With no other live lease, `agent_env_exports` exports nothing for that key
and this second line never prints -- the `eval` line alone is unconditional
(FROB_WORKTREE/FROB_AGENT apply regardless of fleet size; the T-2221 xdist
bound only when relevant), so the output never claims a bound that does
not apply. Best-effort: a resolution failure degrades to a logged warning
naming the manual `eval` command, never a `sys.exit` -- worktree creation
for a solo developer with no fleet context is completely unaffected.

### Acceptance 5: other worktree-creating paths

Audited every `git worktree add`/`_worktree_add_or_reuse` call site under
`src/frob/app/`. Two callers reach `_worktree_add_or_reuse`:
`_work`/`_work_cluster`, both now wired. One other site exists:
`src/frob/app/ticket_runner/_land_cmd.py:2666` (`git worktree add --detach
<tmp_dir> <sha>`), used by land's own internal post-merge/repair machinery
against a throwaway DETACHED worktree at a specific sha -- no interactive
agent shell ever runs there, no `pytest`/`frob` command is ever typed
against it by a human or dispatched agent; it is created, read, and
removed entirely within one `land` invocation. It does not need the hint:
there is no shell session for the hint to reach. No other worktree-creating
path exists in this codebase (grepped `"worktree", "add"` repo-wide). Not
widened beyond `_work`/`_work_cluster`.

### Changed
```
src/frob/app/ticket_runner/_lifecycle.py         | +58 (_print_agent_env_hint, 2 call sites)
tests/test_ticket_work_and_land_finish.py        | +3 tests
```

### Filed
None.
