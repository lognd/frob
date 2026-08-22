## Done report

Changed:
- .claude/hooks/root-write-guard.py :: main, _handle_bash, _handle_file_write,
  _root_write_worktree_paths (new, replaces _agent_worktree_paths),
  _coordinator_marker_set (new), REASON (rewritten)
- tests/test_hook_root_write_guard.py :: full rewrite of the suite for the
  inverted default (20 tests, includes the repro test)
- docs/guides/claude-hooks.md :: `root-write-guard.py` section rewritten to
  describe the T-2850 inversion

Discriminator chosen: the guard now DEFAULT-DENIES any Write/Edit/NotebookEdit/
Bash-detected write into the primary checkout, with a fixed allowlist instead
of a detector: (1) FROB_LAND_INTERNAL=1, (2) tickets.md/tickets/**, (3) the
resolved target sitting inside a REAL, currently-registered linked worktree
(git worktree list --porcelain -- no FROB_AGENT/FROB_WORKTREE check needed
here anymore, since being inside a worktree was never the danger), (4) the
new explicit opt-in FROB_COORDINATOR=1 marker for a human/coordinator shell.
FROB_AGENT/FROB_WORKTREE are no longer read by this hook at all -- the old
_is_agent_context/_worktree_fact discriminator is removed, not repurposed,
because no pairing of those two vars can ever distinguish a pre-worktree
agent from a human (they are environmentally identical in that window,
which is exactly the gap that let both real incidents through).

Each control's result (driven as real PreToolUse JSON payloads through the
actual hook script, subprocess, against this repo's real git worktree
topology -- not just unit tests on helpers):

1. Shell with NEITHER FROB_AGENT nor FROB_WORKTREE, Write to
   src/frob/__init__.py under the real primary checkout -> DENIED (exact
   text below). This is the case that failed before T-2850.
2. Same write, FROB_COORDINATOR=1 set -> ALLOWED (silent, exit 0).
3. Write inside the agent's own real leased worktree
   (.claude/worktrees/t-2850/src/frob/__init__.py via Edit), no markers at
   all -> ALLOWED.
4. tickets.md write, no markers -> ALLOWED.
5. FROB_LAND_INTERNAL=1, write to root src file -> ALLOWED.
6. Bash `echo hi > /home/logan/projects/frob/scratch.py`, no markers ->
   DENIED.
7. Bash `cd <worktree> && frob ticket done-report ...`, no markers ->
   ALLOWED (cd resolves the effective cwd inside a real worktree).
8. Malformed stdin ("not json") -> silent allow, exit 0 (fail-open
   preserved).
9. cwd outside a git repo (/tmp) -> silent allow, exit 0 (fail-open
   preserved).
10. Stale FROB_AGENT=1 + FROB_WORKTREE=<real worktree>, write to root, NO
    FROB_COORDINATOR -> still DENIED (proves the old vars no longer exempt
    a root write on their own -- only the new marker or being inside a
    worktree does).

All ten reproduced with `.claude/hooks/root-write-guard.py`'s real
stdin/stdout contract, both directly against the just-fixed worktree copy
(env -i shells, real `git worktree list`) and via the automated suite.

Exact refusal message text (REASON):

    frob: refusing WRITE to the shared root (T-2850) -- writes to the
    primary checkout are default-DENIED now, not just for detected agent
    shells, because no environment signal reliably tells a pre-worktree
    agent apart from a human. Run `frob ticket work <id>` and edit inside
    your leased worktree instead. (tickets.md/tickets/** are exempt;
    FROB_LAND_INTERNAL=1 covers land's own internal machinery; a genuine
    coordinator/human shell that needs to write here directly sets
    FROB_COORDINATOR=1 once.) If this refusal came AFTER a write already
    landed content in the root, recover it into your worktree rather than
    losing it:
      git diff HEAD -- <paths> > /tmp/rescue.patch   # verify non-empty
      cd <worktree> && git apply --3way /tmp/rescue.patch
      # verify content present, THEN:
      cd <root> && git checkout -- <paths>   # bare form -- restores from
    the index, never `git checkout <branch> -- <path>` (that form can
    silently revert fixes landed since divergence).

Fail-open posture verified unchanged: malformed stdin, missing git, and a
non-repo cwd all still degrade to silent allow (controls 8/9 above).

Scope was widened (frob ticket scope --add) to include
tests/test_hook_root_write_guard.py and docs/guides/claude-hooks.md,
reasoned: the ticket's required behavior change necessarily invalidates
the existing test suite's assertions (which encoded the OLD allow-by-
default contract) and the hook's own doc section; landing the hook change
alone would have broken its own bound evidence.

Repro test: tests/test_hook_root_write_guard.py::test_no_marker_write_to_root_is_refused
designated via --designate-repro against commit aa87d1b6d (the tests-only
commit, hook fix not yet applied) -- verified FAILED_AT_PARENT (a genuine
repro), then passes at the fix commit 5a4118f53.

Evidence: 20 pytest node ids bound (frob ticket evidence T-2850), all
tests/test_hook_root_write_guard.py::test_* -- see ticket ledger for the
full list; all 20 collected and passed
(`uv run pytest tests/test_hook_root_write_guard.py -q` -> exitstatus=0
collected=20 failed=0).

Filed: none. The one out-of-scope item noticed (gate:DUP001 flagging
.claude/hooks/root-write-guard.py::_worktree_paths as duplicating
.claude/hooks/_agent_context.py::_worktree_paths) is PRE-EXISTING --
confirmed byte-identical to the function on main before this ticket's
changes, and already documented/waived from the _agent_context.py side
per that module's own docstring ("root-write-guard.py itself was
deliberately left unmigrated"). Not touched, not filed as new (already a
known, accepted, documented duplication).

Gates: `frob check --only gates-native --ticket T-2850` shows this file's
only findings are pre-existing (identical before/after this ticket's diff,
confirmed by direct byte comparison against the pre-change file):
gate:DUP DUP001 (see above), gate:EXHAUST EXHAUST003/EXHAUST004 warnings on
_git/_file_write_targets_root/main, gate:PERF PERF008 warning on
_bash_redirect_targets_root's pattern.search call. None of these are new
or touched by this diff. The repo-wide DRIFT002/DSL001/PERF004/
claude-config-drift findings the same check run surfaces are main's known
T-2855 fallout / pre-existing claude-config sync drift, unrelated to this
ticket's files, per the brief -- not attributed here and not fixed here.
`--ticket` scopes only gate:SCOPE/PREWORK/the diff-driven COV002/TODO001/
FMT/AFFECT checks to this ticket's touched set (per playbook 6c); the
above per-finding-identity comparison against the pre-change file is the
actual verification that nothing NEW was introduced, not the scoped
gate-summary line.

### Changed
```
 .claude/hooks/root-write-guard.py   | 262 ++++++++++++++------------
 docs/guides/claude-hooks.md         | 111 +++++++-----
 tests/test_hook_root_write_guard.py | 353 ++++++++++++++++++------------------
 tickets/T-2850/ticket.md            |  42 ++++-
 4 files changed, 427 insertions(+), 341 deletions(-)
```

### Evidence
- `tests/test_hook_root_write_guard.py::test_no_marker_write_to_root_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_stale_agent_env_vars_do_not_exempt_a_root_write` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_coordinator_marker_allows_a_root_write` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_write_inside_a_real_worktree_is_allowed_with_no_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_write_inside_a_nested_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_fake_worktree_looking_path_does_not_exempt_a_root_write` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_ledger_paths_are_exempt_with_no_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_frob_land_internal_exempts_a_root_write_with_no_other_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_non_guarded_tool_is_ignored` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_with_no_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_refusal_names_the_recovery_recipe` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_coordinator_marker_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_cd_into_worktree_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_explicit_path_flag_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_redirect_into_primary_with_no_marker_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_redirect_inside_worktree_is_allowed_with_no_markers` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_ambiguous_redirect_target_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_read_only_ticket_verb_is_never_refused` (pytest node id, verified passing when recorded)
- `tests/test_hook_root_write_guard.py::test_bash_unrelated_command_is_never_refused` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 54 error(s), 499 warning(s), 796 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-2396, COV003@tickets/T-2442, COV003@tickets/T-2481, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC006@docs/modules/graph.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@docs/modules/tickets-landing.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DSL001@tests/unit/test_coordinator_scripts.py, DUP001@.claude/hooks/root-write-guard.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2850/src/frob/gates/_mutation_evidence.py, F822@/home/logan/projects/frob/.claude/worktrees/t-2850/src/frob/gates/_bug_repro.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2850, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
