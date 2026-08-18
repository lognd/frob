## Done report

Fix shape chosen: extended the PreToolUse edit-time hook itself
(.claude/hooks/root-write-guard.py) to also match Bash, rather than
moving the check inside frob's own ticket-mutating verbs. Rationale:
frob.tickets._worktree_guard.enforce_worktree_lease already implements
the "verb refuses when cwd != FROB_WORKTREE" check the ticket's
suggested complementary fix describes, and it is already wired into
every mutating frob.tickets entry point -- yet it did not catch the
measured done-report incident, because FROB_WORKTREE is env-based and
this harness resets environment/cwd state between Bash calls the same
way it resets cwd; a verb-side check inherits the exact same blind spot
the hook-side check has to work around (T-2071's own finding: FROB_AGENT/
FROB_WORKTREE measured UNSET in real agent shells). The PreToolUse hook
is the one place Claude Code's own hook surface can see the call BEFORE
the write happens, independent of whether the invoking shell happened to
carry lease env this time. Kept the ticket's suggested verb-level
check as a documented future option in the follow-up ticket rather than
building it now, to keep this ticket's diff to the one proven mechanism.

Changed:
.claude/hooks/root-write-guard.py::_GUARDED_TOOLS (Bash added)
.claude/hooks/root-write-guard.py::_MUTATING_TICKET_VERBS (new)
.claude/hooks/root-write-guard.py::_TICKET_VERB_RE (new)
.claude/hooks/root-write-guard.py::_LEADING_CD_RE (new)
.claude/hooks/root-write-guard.py::_REDIRECT_TARGET_RES (new)
.claude/hooks/root-write-guard.py::_AMBIGUOUS_PATH_CHARS (new)
.claude/hooks/root-write-guard.py::_strip_quotes (new)
.claude/hooks/root-write-guard.py::_leading_cd_target (new)
.claude/hooks/root-write-guard.py::_resolve_relative (new)
.claude/hooks/root-write-guard.py::_under_any (new)
.claude/hooks/root-write-guard.py::_unambiguous_target (new)
.claude/hooks/root-write-guard.py::_effective_cwd (new)
.claude/hooks/root-write-guard.py::_resolves_under_primary (new)
.claude/hooks/root-write-guard.py::_bash_ticket_verb_targets_root (new)
.claude/hooks/root-write-guard.py::_bash_redirect_targets_root (new)
.claude/hooks/root-write-guard.py::_bash_targets_root (new)
.claude/hooks/root-write-guard.py::_agent_worktree_paths (new)
.claude/hooks/root-write-guard.py::_handle_bash (new)
.claude/hooks/root-write-guard.py::_file_write_targets_root (new)
.claude/hooks/root-write-guard.py::_handle_file_write (new, extracted
  from the pre-existing main() body, logic unchanged)
.claude/hooks/root-write-guard.py::main (updated to branch on tool_name)
.claude/settings.json (PreToolUse matcher widened to include Bash)
docs/guides/claude-hooks.md (root-write-guard.py section updated)
tests/test_hook_root_write_guard.py (9 new test_bash_* cases; updated
  test_non_guarded_tool_is_ignored to use a genuinely non-guarded tool
  now that Bash is guarded)

Evidence:
tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_and_no_path_is_refused (accepts 0)
tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_cd_into_worktree_is_allowed (accepts 1)
tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_explicit_path_flag_is_allowed (accepts 1)
tests/test_hook_root_write_guard.py::test_bash_ticket_verb_from_human_or_coordinator_shell_is_allowed (accepts 2)
tests/test_hook_root_write_guard.py::test_bash_ambiguous_redirect_target_is_allowed (accepts 3)
Full file: 19/19 passed (tests/test_hook_root_write_guard.py, pytest -q,
SUITE-RESULT: exitstatus=0 collected=19 failed=0), including the pre-
existing T-2396/T-2412 cases (nested-worktree topology, ledger exemption,
FROB_LAND_INTERNAL, human/coordinator non-fire) -- all still pass
unchanged.

Empirical verification (all four acceptance criteria, against a REAL
nested-worktree fixture at primary/.claude/worktrees/agent-wt, the actual
deployment topology per T-2442, not the sibling shape):
[0] must-refuse: `frob ticket done-report T-9999 --why done` from the
    primary checkout, FROB_AGENT=1/FROB_WORKTREE=<worktree> -> denied.
[1] must-still-allow: same command with `cd <worktree> &&` prefix, and
    separately with `--path <worktree>` -- both -> allowed (no output).
[2] must-still-allow-human: identical command, no FROB_AGENT/
    FROB_WORKTREE at all -> allowed.
[3] must-not-overblock: `echo hi > "$OUTFILE"` (unresolvable target) in
    agent context, no cd -> allowed, not refused.
Ran these directly against the compiled hook via subprocess (matching
the test file's own harness pattern) both before and after the ARCH103/
COV002/E501 cleanup pass, to confirm the refactor did not change
behavior.

Gates: `frob check --land-parity` (T-1535) run repeatedly through the
fix; final unscoped error set contains ZERO findings against
.claude/hooks/root-write-guard.py, .claude/settings.json,
docs/guides/claude-hooks.md, or tests/test_hook_root_write_guard.py.
Confirmed via `frob check --ticket T-2481 --only test` (0 errors) and
`--only archgate`/`--only coverage` scoped runs (the sole unwaived
findings in each -- src/frob/release/_cli.py ARCH103, and pre-existing
gates/_port_selfcheck.py, gates/_refs_schema.py, tickets/T-1205 etc. --
are unrelated pre-existing files/tickets this ticket never touched).
SEC110 on .claude/hooks/root-write-guard.py is PRE-EXISTING (all 3
os.environ.get() call sites predate this ticket, confirmed via
`git show main:.claude/hooks/root-write-guard.py`; no new env-read site
was added). 13 new private symbols carry `frob:waive COV005` with the
same reason precedent already established at
src/frob/gates/_coverage_sites.py (brand-new private helper, not an
extraction that silently rode an existing doc anchor away from a public
symbol).

Filed: T-2487 (renumbers at land) -- "add a post-Bash
root-cleanliness detector for agent context (complementary to T-2481's
guard)", per the coordinator's mid-task evidence of a fourth incident
caught fast via `git status` + `git checkout --` rather than late at
land time. Out of scope for T-2481 (a different mechanism -- PostToolUse
detection vs. this ticket's PreToolUse inference) but recorded as a
strong complementary follow-up.

Gates: frob check --land-parity clean of any finding against this
ticket's scope (verified via repeated re-runs through the fix; see
above). No RULE-ID waived at file:line without the explicit COV005
reasons documented above; SEC110 is disclosed as pre-existing, not
waived by this ticket (out of scope to fix).

### Changed
```
 .claude/hooks/root-write-guard.py   | 388 ++++++++++++++++++++++++++++++++----
 .claude/settings.json               |   2 +-
 docs/guides/claude-hooks.md         |  41 +++-
 tests/test_hook_root_write_guard.py | 161 ++++++++++++++-
 tickets/T-2481/ticket.md            |  50 ++++-
 tickets/T-2487/ticket.md  |  60 ++++++
 6 files changed, 649 insertions(+), 53 deletions(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_and_no_path_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_cd_into_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_explicit_path_flag_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_from_human_or_coordinator_shell_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ambiguous_redirect_target_is_allowed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2481/src/frob/app/ticket_runner/_waive_audit.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2481, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
