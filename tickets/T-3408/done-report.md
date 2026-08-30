## Done report

Checked first, per the ticket's own requirement: read the pre-T-3408
`sync-claude-config.py` in full -- `plan()` compared each managed source's
rendered content to the CURRENT destination content only, with no notion
of "behind" vs "ahead" and no ancestry/diff guard of any kind. Confirmed
by reading the source, not assumed.

Root cause: every worktree carries its own copy of `MANAGED`'s source
files; `~/.claude/` is materialized FROM whichever worktree last ran this
script, and is shared by every process on the machine. A worktree that
branched before a sibling's hook fix landed on `main` could run the sync
and silently revert that fix globally, with no diff, no warning, no
record -- measured live 2026-08-29 (series EQ's sync clobbered series
ER's in-flight `frob-suggest.py` fix, caught only by an agent diffing by
chance).

Policy chosen, with reasoning (the ticket's own three-option menu):
option (b) -- refuse to sync a specific managed file when this worktree's
own copy of it is BEHIND `main` (unchanged since branching, while `main`
has since moved the file), implemented via `stale_managed_sources`/
`_is_source_stale_vs_main` using `git merge-base main HEAD` plus per-file
`git show`. NOT option (a) (main-only): would cost every agent the
ability to test a hook change in place, a real workflow this repo relies
on. NOT bare option (c) (destination-diff-and-confirm alone): the
destination can be behind main too with nothing at risk, which would
demand an override for a perfectly safe forward sync; checking directly
against `main` is the more precise question and matches what the
measured incident actually was. (c)'s own escape hatch is folded in
regardless: `--allow-stale` overrides the refusal explicitly, per file.
A worktree's OWN edit to a managed file is never treated as stale no
matter how far `main` has moved on the same file meanwhile -- the
in-place-testing case this policy exists to preserve (MUST-STAY-QUIET).
Deliberately not a lock (the ticket's explicit "do not"): serializing
writers still lets the stale one win once it is its turn.

`plan()`'s own public signature is UNCHANGED (still `(actions, missing)`)
so `frob.app.claude_runner.drift_report`/`drift_warning` -- which runs on
every `frob` invocation -- keeps its existing fast, git-free contract;
the new git-backed staleness check runs only on the WRITE path (`main`),
which is infrequent, not on every command.

Filed: none.

Gates: `frob check --ticket T-3408` clean, 0 errors (after adding
ARCH103/WIRE001 waivers matching this repo's own existing precedent
shapes for identical patterns). `frob test --base main` pass (6
outcomes, exit=0); node-id pytest -p no:xdist on the new stale-guard test
file plus the existing claude_runner tests: 14 passed, 0 failed.
Designated repro (`--designate-repro`) confirmed FAILED_AT_PARENT against
a test-only commit predating the fix.

### Changed
```
 .claude/hooks/sync-claude-config.py                | 209 ++++++++++++++++++-
 docs/guides/claude-hooks.md                        |  32 +++
 .../test_sync_claude_config_stale_guard_t3408.py   | 223 +++++++++++++++++++++
 tickets/T-3408/ticket.md                           |  25 ++-
 4 files changed, 485 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_unmodified_source_behind_main_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_worktree_own_edit_is_never_stale_even_if_main_also_moved` (pytest node id, verified passing when recorded)
- `tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_source_matches_main_is_not_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_unknown_git_readings_fail_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal::test_stale_file_skipped_forward_file_synced` (pytest node id, verified passing when recorded)
- `tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal::test_allow_stale_overrides_the_refusal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 10 error(s), 4082 warning(s), 865 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
