## Done report

Built the complementary PostToolUse detector T-2481 filed itself: a
`Bash`-matched PostToolUse hook (`.claude/hooks/root-cleanliness-detector.py`)
that runs `git status --porcelain` against the PRIMARY checkout right
after every Bash call in agent context and, when it finds dirt, prints a
`systemMessage` naming every dirtied path with its exact one-line
recovery command (`git checkout --` for a tracked change, `git clean
-fd --` for something untracked) -- confirmed against Claude Code's own
hooks reference (fetched during this ticket): PostToolUse supports no
`decision`/`hookSpecificOutput` fields (the tool already ran, so nothing
can be blocked), only the universal `systemMessage`/`continue` pair, so
this is the correct, documented non-blocking feedback channel. This has
NO overblock failure mode by construction -- a report-only hook cannot
obstruct legitimate work, the risk that constrained T-2481's design.

Shared discriminator extracted to `.claude/hooks/_agent_context.py`
(`_git`/`_worktree_paths`/`_worktree_fact`/`_is_agent_context`, the
IDENTICAL logic T-2481's `root-write-guard.py` already carried) --
extracted per CLAUDE.md's no-duplication rule the first time a SECOND
hook needed it. `root-write-guard.py` itself was deliberately left
unmigrated (a just-landed, independently-tested PreToolUse guard, not
worth touching purely for reuse with zero behavior change); the residual
duplication between the two files is disclosed and `frob:waive DUP001`d
with that reasoning, matching this repo's own precedent for standalone
hook files (`tests/test_hook_root_write_guard.py`'s `_run_hook`/
`_denial_reason` DUP001 waiver).

Changed:
.claude/hooks/_agent_context.py (new module: _git, _worktree_paths,
  _worktree_fact, _is_agent_context)
.claude/hooks/root-cleanliness-detector.py (new hook: _GUARDED_TOOLS,
  _dirty_entries, _recovery_command, _report, _decision, main)
.claude/hooks/root-write-guard.py (SEC110 waivers added on its 3
  pre-existing os.environ.get() sites, per the coordinator's explicit
  ask -- trivial and in scope; no behavior change)
.claude/hooks/sync-claude-config.py (MANAGED manifest: added both new
  hook files so `~/.claude/hooks/` stays in sync -- the exact drift class
  that caused an earlier incident today)
.claude/settings.json (new PostToolUse/Bash matcher entry)
design/frob.strata (testsuite node: added the new test file to its
  `exec`/`fs.write` may-declarations, plus a frob:ticket edge)
docs/guides/claude-hooks.md (new `_agent_context.py` and
  `root-cleanliness-detector.py` sections)
tests/test_hook_root_cleanliness_detector.py (new, 6 cases)

Evidence:
tests/test_hook_root_cleanliness_detector.py::test_clean_root_in_agent_context_is_silent
tests/test_hook_root_cleanliness_detector.py::test_dirty_root_in_agent_context_is_reported
tests/test_hook_root_cleanliness_detector.py::test_dirty_root_from_human_or_coordinator_shell_is_silent
tests/test_hook_root_cleanliness_detector.py::test_dirty_root_reported_even_when_cwd_is_the_worktree
tests/test_hook_root_cleanliness_detector.py::test_frob_land_internal_exempts_dirty_root
tests/test_hook_root_cleanliness_detector.py::test_non_bash_tool_is_ignored
25/25 passed across both hook test files (tests/test_hook_root_
cleanliness_detector.py + tests/test_hook_root_write_guard.py, pytest -q,
SUITE-RESULT: exitstatus=0 collected=25 failed=0) -- confirms T-2481's
guard is unaffected by this ticket's SEC110-waiver edit to it.

Empirical verification (both discriminator directions, plus every
exemption), against a REAL nested-worktree fixture with a `.gitignore`
excluding `.claude/worktrees/` -- matching this repo's own tracked
`.gitignore:33` exactly, run both as a throwaway fixture AND directly
against this repo's own real checkout (root clean -> zero output,
confirming no false positive in the actual deployment topology):
- clean primary + agent context -> silent
- dirty primary (1 modified, 1 untracked) + agent context -> systemMessage
  naming BOTH paths with exact recovery commands (`git checkout --
  "README.md"`, `git clean -fd -- "stray.txt"`)
- dirty primary + NO FROB_AGENT/FROB_WORKTREE (human/coordinator) ->
  silent -- discriminator confirmed in both directions, same posture as
  T-2396/T-2481
- dirty primary, Bash call's cwd was the (clean) agent worktree -> still
  reported (checks paths[0], the primary, not whatever cwd the
  triggering call happened to use)
- FROB_LAND_INTERNAL=1 -> silent (land's own escape hatch, matching
  root-write-guard.py's precedent)
- non-Bash tool (Read) -> silent (this hook only ever fires after Bash)

Gates: `frob check --land-parity` (T-1535), run to convergence through
three fix rounds. Final unscoped error set contains ZERO findings
against any file this ticket touched -- confirmed via `git grep`
matching against the 30-line ERROR list, none naming
_agent_context.py/root-cleanliness-detector.py/root-write-guard.py/
sync-claude-config.py/settings.json/design/frob.strata/the new test
file. Fixed along the way (all now `frob:waive`d with real, disclosed
reasons, never a hollow waiver): DUP001 x3 (_agent_context.py's _git/
_worktree_paths duplicating root-write-guard.py's copies by design;
root-cleanliness-detector.py's main() sharing the standard hook-
entrypoint shape every hook in this directory repeats), SEC110 x3 (the
3 new os.environ.get() reads this ticket introduced: FROB_WORKTREE/
FROB_AGENT in _agent_context.py, FROB_LAND_INTERNAL in
root-cleanliness-detector.py -- all dispatch-context markers, no secret
value, same posture as every other SEC110 waiver on this exact variable
class already in this repo), COV002 (design/frob.strata's testsuite-node
edit needed its own frob:ticket edge, added to the existing stacked
block above `node testsuite`).

SEC110 on `root-write-guard.py` (T-2481's own file, flagged in that
ticket's Done report as pre-existing/out-of-scope): resolved per the
coordinator's explicit request in this ticket's brief. Trivial and
genuinely in scope (T-2487's scope includes `.claude/hooks/`): 3
`frob:waive SEC110` comments added, reusing the exact reason text
`src/frob/tickets/_leases.py`'s own FROB_AGENT/FROB_WORKTREE precedent
established, no behavior change (verified: root-write-guard.py's own
19-test suite still 19/19 green).

Filed: none. No out-of-scope discoveries this ticket needed to defer.

### Changed
```
 .claude/hooks/_agent_context.py              | 135 +++++++++++++++++
 .claude/hooks/root-cleanliness-detector.py   | 211 +++++++++++++++++++++++++++
 .claude/hooks/root-write-guard.py            |  50 ++++++-
 .claude/hooks/sync-claude-config.py          |   5 +
 .claude/settings.json                        |  13 ++
 design/frob.strata                           |   5 +-
 docs/guides/claude-hooks.md                  |  60 ++++++++
 tests/test_hook_root_cleanliness_detector.py | 194 ++++++++++++++++++++++++
 tickets/T-2487/ticket.md                     |  70 ++++++++-
 9 files changed, 734 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_hook_root_cleanliness_detector.py::test_clean_root_in_agent_context_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_dirty_root_in_agent_context_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_dirty_root_from_human_or_coordinator_shell_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_dirty_root_reported_even_when_cwd_is_the_worktree` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_frob_land_internal_exempts_dirty_root` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_cleanliness_detector.py::test_non_bash_tool_is_ignored` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2487, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
