## Done report

## Done report

Changed:
- src/frob/tickets/_leases.py -- new `WorktreeSweepError`, `WorktreeVerdict`,
  `_is_agent_worktree_path`, `list_agent_worktrees`, `_worktree_is_clean`,
  `_worktree_head_age_seconds`, `sweep_worktrees`. Reuses the existing
  `read_all_leases`/`is_lease_ttl_expired`/`lease_age_seconds` lease
  machinery for liveness -- does not reimplement it.
- src/frob/app/worktree_runner.py (new file, scope-added) -- self-contained
  `frob worktree sweep` CLI runner, mirroring `frob.app.agent_runner`'s
  precedent (direct `__main__._dispatch`, no `AppConfig`/`App` routing).
- src/frob/__main__.py (scope-added) -- registers the `worktree` subcommand
  tree for --help discovery and the direct-dispatch branch, mirroring the
  existing `bind`/`agent` branches.
- README.md (scope-added) -- new `frob worktree` command-table row and
  command-count bump (32 -> 33); required by this repo's own DOC005 gate.
- docs/guides/agent-playbook.md -- new section 12b, "Coordinator worktree
  cleanup (T-0836)": mandates `frob worktree sweep` (or a per-worktree
  verify-then-remove for a single just-landed ticket) and forbids raw bulk
  `git worktree remove` loops across `.claude/worktrees/*`.
- tests/test_ticket_leases.py -- 9 new tests (fixture repos with real
  `.claude/worktrees/`-shaped linked worktrees, real lease files, real git
  state; no mocking of the lease or git layers).

Behavior implemented exactly per the ticket's Fix section:
- `frob worktree sweep [path] [--dry-run] [--min-age HOURS]`.
- Enumerates git-registered worktrees via `git worktree list --porcelain`,
  filtered to `.claude/worktrees/`-shaped paths.
- Removes a candidate ONLY IF (a) `git status --porcelain` is empty AND
  (b) no live (unexpired) lease among `read_all_leases()` is pinned to it
  -- an EXPIRED lease does not block removal, matching the T-0782 dead-
  agent recovery precedent.
- `--min-age HOURS` adds a third gate on HEAD commit age
  (`git log -1 --format=%ct`); an unresolvable age is treated
  conservatively (kept, never removed).
- Prints one verdict line per worktree (`removed` /
  `kept:lease(<ticket> <age>)` / `kept:dirty` / `kept:age`) plus a summary
  count line.
- Removal is exclusively `git worktree remove <path>` -- never deletes a
  branch. Verified directly (`test_branches_survive_removal`).
- `--dry-run` computes the same verdicts but never calls `git worktree
  remove` (`test_dry_run_removes_nothing`).

Manual smoke test against the REAL repo (`frob worktree sweep --dry-run
/home/logan/projects/frob`) correctly reported `kept:dirty` for the two
worktrees with uncommitted state (including this one) and a would-be
`removed` for a third, clean, lease-free worktree -- no worktree was
actually touched (dry-run).

Evidence: 9 pytest node ids (all under tests/test_ticket_leases.py),
recorded via `frob ticket evidence T-0836`:
- TestListAgentWorktrees::test_lists_only_dot_claude_worktrees_paths
- TestSweepWorktrees::test_clean_no_lease_removed
- TestSweepWorktrees::test_clean_live_lease_kept
- TestSweepWorktrees::test_dirty_kept
- TestSweepWorktrees::test_expired_lease_clean_removed
- TestSweepWorktrees::test_dry_run_removes_nothing
- TestSweepWorktrees::test_branches_survive_removal
- TestSweepWorktrees::test_min_age_keeps_recent_worktree
- TestWorktreeSweepCli::test_sweep_cli_prints_verdicts_and_summary
All 9 (plus the file's prior 7 T-0835 tests, 16 total) pass:
`uv run pytest tests/test_ticket_leases.py -q` -> 16 passed.
`ruff check`/`ruff format --check`/`ty check` all clean on every touched
file.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-0836` run chunked (section 3b's sanctioned
loop, `--only lint/static/gates-fast/gates-native/gates-security`) --
every stage-group PASS, 0 attributable errors. The two new-but-pre-
existing-style findings this ticket's own additions triggered (DOC005:
README table drift; PRE001: stale pre-work sweep after a scope change)
were fixed in-scope (README row + count, `frob ticket sweep T-0836`
re-run) rather than waived. `frob ticket scope --add` used three times
(worktree_runner.py, __main__.py, README.md) with `--reason-file`, all
minimal and mechanical per the ticket's own precedent instruction.

Deviations from the ticket's literal wiring hint: the ticket scope listed
`src/frob/app/ticket_runner.py` as in-scope, but `frob worktree` is wired
as its own self-contained direct-dispatch command (like `frob agent`/
`frob bind`), not through `frob ticket`'s `AppConfig`/`App` dispatch
table -- `ticket_runner.py` was not touched, since there was no natural
hook point there for a non-ticket command. This matches the ticket's own
explicit precedent instruction ("frob agent ... is a small self-contained
runner ... follow that same pattern").

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_leases.py::TestListAgentWorktrees::test_lists_only_dot_claude_worktrees_paths` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_clean_no_lease_removed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_clean_live_lease_kept` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_dirty_kept` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_expired_lease_clean_removed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_dry_run_removes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_branches_survive_removal` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestSweepWorktrees::test_min_age_keeps_recent_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeSweepCli::test_sweep_cli_prints_verdicts_and_summary` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 1203 warning(s), 210 waived
