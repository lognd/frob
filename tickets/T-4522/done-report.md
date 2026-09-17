## Done report

T-4522 -- flatten single-child verb groups (partial: claude, natives)

What changed:
- src/frob/_cli_parsers/_misc.py:
  - _add_claude_parser: claude_p.set_defaults(claude_command="sync") so
    bare `frob claude` dispatches to `sync`; mirrored sync_p's `--check`
    flag onto claude_p itself (same dest, claude_check) so `frob claude
    --check` (no `sync`) behaves identically to `frob claude sync
    --check`; added a `description=` to claude_p documenting the T-4522
    alias so it shows in `frob claude --help` (argparse only prints a
    subparser's `help=` string from the PARENT's --help, not its own).
  - _add_natives_parser: natives_p.set_defaults(natives_command="build")
    plus a mirrored `--path` argument (same dest, natives_path, default
    ".") on natives_p itself, and a matching `description=` note.
- tests/unit/test_cli_single_child_groups.py (new): 8 tests -- for each
  of claude/natives: bare form defaults the dispatch dest, bare form
  honors the child's own flag, two-word form still parses identically,
  and --help on the group shows "T-4522".

Why partial (3 of 5 groups NOT done, deliberately, not silently):
- agent env / worktree sweep: both parsers are registered in
  src/frob/_cli_parsers/_core.py. `frob ticket start T-4522` refused
  with a scope collision: T-4523 (state=queued but with a LIVE worktree
  at .claude/worktrees/t-4523) holds an active lease on _core.py for an
  unrelated scaffold-pool-dead-code ticket. Per the brief's hard rule
  ("a lease refusal naming another ticket means stop and report, never
  --steal"), I narrowed T-4522's declared scope to remove _core.py
  (`frob ticket scope T-4522 --remove src/frob/_cli_parsers/_core.py
  --reason "..."`) rather than force through it. agent/worktree
  flattening is left for a follow-up once T-4523 lands or is
  coordinated.
- narrative move: `add_narrative_parser` is defined in
  src/frob/narrative/_cli.py and wired in from
  src/frob/_cli_parsers/_root.py (git grep confirms: no "narrative"
  symbol at all in _misc.py or _core.py). Both of those files are
  outside T-4522's declared scope (_root.py is also one of the
  explicitly-leased-elsewhere files named in this drive's amendments).
  Flattening it would require touching files this ticket does not own.

Caller-count invariant (brief's required check), same command run
before implementing and after, inside the worktree:
  git grep -n -E 'frob (agent env|claude sync|natives build|narrative move|worktree sweep)' -- .claude .github docs scripts src tests | wc -l
  -> 205 both times (unchanged -- the two-word spelling was never
  altered, only a default added alongside it, so every existing caller
  stays valid).

Verification run (per amendment (b), no ticket-scoped `frob check`, no
`frob ticket done-report`):
- ruff check src/frob/_cli_parsers/_misc.py tests/unit/test_cli_single_child_groups.py
    -> All checks passed!
- ruff format --check (after running ruff format once to apply the
  project's own style) on the same two files -> both already formatted.
- ty check src/frob/_cli_parsers/_misc.py tests/unit/test_cli_single_child_groups.py
    -> All checks passed!
- pytest -p no:xdist -p no:cacheprovider, PYTHONPATH=<WT>/src, serial:
    tests/unit/test_cli_single_child_groups.py -> 8 passed
    tests/unit/test_claude_runner.py tests/unit/test_natives_build.py
      tests/unit/test_main_entry.py -> 82 passed (pre-existing
      claude/natives/dispatch tests, run to confirm no regression)

Out-of-scope findings to file (not fixed, per hard rules):
- T-4523's ticket.md state reads "queued" but a live worktree exists
  at .claude/worktrees/t-4523 with an active file lease on _core.py --
  worth flagging to the coordinator as a possible ledger/worktree state
  drift (state should probably read in-progress), though this may just
  be a start-in-flight snapshot race and not a bug.
- Follow-up ticket needed to flatten `agent env` and `worktree sweep`
  in _core.py once T-4523's lease clears.
- Follow-up ticket (or scope amendment) needed to flatten `narrative
  move`, scoped to src/frob/_cli_parsers/_root.py and/or
  src/frob/narrative/_cli.py.

Worktree: /home/logan/projects/frob/.claude/worktrees/t-4522
Branch: t-4522
HEAD: 4fbff8c78 feat(cli): flatten frob claude/natives single-child verb groups (T-4522)
git -C <WT> status --short: empty

Status: READY (for the claude/natives portion actually in scope; the
agent/worktree/narrative portion is explicitly deferred and reported
above, not silently dropped).

### Changed
```
 src/frob/_cli_parsers/_misc.py             |  56 ++++++++++++---
 tests/unit/test_cli_single_child_groups.py | 106 +++++++++++++++++++++++++++++
 tickets/T-4522/ticket.md                   |  18 ++++-
 3 files changed, 169 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened::test_bare_claude_defaults_to_sync` (pytest node id, verified passing when recorded)
- `tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened::test_bare_natives_defaults_to_build` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 27 error(s), 4936 warning(s), 978 waived
- error-findings: ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, CROSSTICKET001@design/frob.strata, CROSSTICKET001@docs/commands/check.md, CROSSTICKET001@docs/design/registry/capability-via-ratchet.lock.json, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@docs/modules/lang.md, CROSSTICKET001@docs/modules/tickets-landing.md, CROSSTICKET001@src/frob/__main__.py, CROSSTICKET001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@src/frob/_cli_parsers/_ticket/_progress.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/check_runner.py, CROSSTICKET001@src/frob/app/config.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/dup/_legacy_cs.py, CROSSTICKET001@src/frob/gates/__init__.py, DOC005@docs/modules/cli.md, DUP002@tests/unit/test_cli_single_child_groups.py, MILE001@tickets.md, PERF004@src/frob/doctor.py, PRE001@tickets/T-4522, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4550.json, WIRE002@src/frob/dup/_legacy_cs.py, invalid-argument-type@tests/unit/test_ticket_runner_land_cmd_flags.py
