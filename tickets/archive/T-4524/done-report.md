## Done report

T-4524: replace the 20 --skip-<stage> flags with one repeatable --skip
STAGE[,STAGE] mirroring --only

WHAT CHANGED

src/frob/_cli_parsers/_check.py
  - New _SKIP_STAGE_FIELDS dict: canonical stage name -> the exact
    AppConfig.check_skip_<stage> attribute name the pre-existing legacy
    flags already used (20 entries: ruff, ruff-check, ruff-format, ty,
    arch, cycle, dup, bind, exports, gates, tests, build, clang-tidy,
    clang-format, cargo-check, clippy, fmt, tsc, eslint, prettier).
  - New _SkipStageAction(argparse.Action): backs the new --skip flag.
    Splits its value on commas, looks each stage up in
    _SKIP_STAGE_FIELDS, and setattr()s the SAME namespace attribute the
    matching legacy flag sets. An unknown stage calls parser.error()
    (exit 2) naming the bad stage and the full known vocabulary.
  - New _add_check_skip_unified_arg(check_p): registers --skip
    (dest=check_skip_stages, action=_SkipStageAction, repeatable).
  - New _HideDeprecatedFormatter(argparse.HelpFormatter): overrides
    add_argument and add_usage to omit any action whose help string
    starts with "DEPRECATED" from the rendered --help block (both the
    usage line and the options body), while the action stays fully
    registered/parseable and its real help string is still visible to
    anything that introspects the parser's _actions directly.
  - Every one of the 20 legacy --skip-<stage> flags (including
    --skip-tests, which lived in _add_check_scope_args) now carries
    help=_deprecated_skip_help(stage), a string starting with
    "DEPRECATED (T-4524): use --skip <stage> instead".
  - _add_check_parser now passes formatter_class=_HideDeprecatedFormatter
    to sub.add_parser("check", ...) and calls
    _add_check_skip_unified_arg(check_p) alongside the existing
    _add_check_skip_args(check_p) call.
  - The four _add_check_skip_args/_python/_cpp/_rust_ts function names
    are unchanged (same names, same call sites) -- no shim needed, they
    were never renamed, only had help= text added.

src/frob/_cli_parsers/__init__.py
  - Re-exports the new _add_check_skip_unified_arg alongside the
    existing four _add_check_skip_args* re-exports, and adds it to
    __all__.

src/frob/app/check_runner.py
  - New _refuse_skip_only_conflict(cfg) -> str | None: returns the first
    stage name present in both cfg.check_only and a True
    cfg.check_skip_<stage> field (via _SKIP_STAGE_FIELDS, imported
    lazily from frob._cli_parsers._check to avoid a new module-level
    cross-package import at collection time), or None if disjoint.
  - run(cfg) now calls this right after the root.exists() check and
    before _handle_early_exit_modes; a non-None result logs
    "--skip and --only both name stage %r -- drop one" and sys.exit(1).

docs/commands/check.md
  - "Skip flags" section rewritten around --skip STAGE (comma-split,
    repeatable, full stage-name list, refusal-on-conflict-with---only
    documented with an example), with a "Deprecated per-stage flags"
    subsection listing all 20 legacy spellings and their one-release
    sunset.
  - The cpp/rust/typescript mode example blocks and the "TypeScript
    skip flags" section were updated from --skip-<stage> to the new
    --skip <stage>[,<stage>] syntax.

tests/unit/test_check_skip_flag.py (new)
  - TestUnifiedSkipFlag: comma-split sets the same attrs as the legacy
    pair; repeatable; whitespace around commas trimmed; unknown stage
    exits 2 naming the bad value; --skip ruff sets only check_skip_ruff
    (the bundle, not the split flags -- matches T-2320's existing OR
    downstream); every one of the 20 _SKIP_STAGE_FIELDS entries maps to
    a real AppConfig field.
  - TestLegacyFlagsDeprecated: all 20 legacy flags still parse;
    --help's rendered token set contains none of the 20 --skip-<stage>
    spellings (checked as whole tokens, not substrings, since the new
    --skip flag's own help text mentions "ruff-skip" prose); every
    legacy action's real (unrendered) help string starts with
    "DEPRECATED" (20 found).
  - TestSkipOnlyConflict: overlap detected/returns the stage name;
    disjoint stages return None; no --only means no conflict; a full
    run(cfg) call exits 1 and logs the stage name.
  32 tests total, all pass serially (see command below).

MEASURED

ruff check on the 4 touched src/test files: All checks passed!
ruff format --check on the 4 touched src/test files: all formatted
  (one reformat applied to the new test file, then clean).
ty check on the 4 touched src/test files: All checks passed! (one
  narrowing fix needed in the test: argparse's _subparsers/_group_actions/
  choices attrs are typed as X | None at the stub level; followed the
  exact narrowing pattern tests/unit/test_cli_hygiene_checklist_t1556.py
  already uses for the same shape rather than inventing a new one).

  PYTHONPATH=<WT>/src /home/logan/projects/frob/.venv/bin/python -m pytest
    -q -p no:cacheprovider -p no:xdist tests/unit/test_check_skip_flag.py
  -> 32 passed, exitstatus=0

Also ran (regression check, not scope, no changes needed):
  tests/unit/test_app_config_flag_coverage.py tests/unit/test_check.py
  tests/unit/test_check_budget.py tests/unit/test_app_runners_batch6.py
  tests/unit/test_cycle_waiver.py tests/unit/test_ticket_runner_gate_findings.py
  -> 308 passed, exitstatus=0
  (test_app_config_flag_coverage.py matters here specifically: it
  intersects every parser dest with AppConfig.model_fields, so the new
  --skip flag's dummy dest check_skip_stages -- which deliberately does
  NOT exist on AppConfig, since config.py/_config_external.py are out of
  this ticket's scope -- is naturally excluded rather than flagged as a
  dropped-flag defect.)

DESIGN DECISIONS / JUDGMENT CALLS

1. No new AppConfig field. config.py and _config_external.py are both
   outside this ticket's declared scope, so the unified --skip flag
   cannot introduce a new forwarded config field. Instead the argparse
   Action directly sets the SAME check_skip_<stage> namespace attributes
   the legacy per-flag dests already set and that are already forwarded
   -- this is the literal reading of "mapping onto the existing skips
   dict so nothing downstream changes" and it is verified true:
   check_runner.py's stage dispatch code (_python_skip_flags and friends)
   is untouched.

2. "Hidden from the main help block" + "tagged DEPRECATED in its help
   string" are in tension under stock argparse: argparse.SUPPRESS
   replaces help text entirely, so a flag cannot be both invisible AND
   carry readable DEPRECATED text through the same help= kwarg. Resolved
   with a custom HelpFormatter (_HideDeprecatedFormatter) that renders
   normally but drops any DEPRECATED-tagged action from both the usage
   line and the options body -- so --help output genuinely has 20 fewer
   flags (measured: 0 legacy tokens in --help's rendered word set) while
   action.help on the actual argparse.Action objects still reads
   "DEPRECATED (T-4524): use --skip <stage> instead" for any caller that
   introspects the parser directly (e.g. a future removal-readiness
   check, or a doc generator). This is the module's own documented
   design (see _HideDeprecatedFormatter's docstring in the diff).

3. The --skip/--only overlap refusal lives in check_runner.run(), not in
   argparse itself, because the two flags can appear in either order on
   the command line and an argparse Action only sees state as of the
   moment it fires -- by the time AppConfig is built, both check_only
   and every check_skip_<stage> boolean are final regardless of arg
   order, so that is the first point a complete, order-independent
   comparison is possible. The check is overlap-based (any stage that is
   both True in check_skip_<stage> and named in check_only), which also
   catches an old --skip-<stage> flag combined with --only on the same
   stage, not just the new --skip -- a stricter behavior than the ticket
   literally required but consistent with it (same shape of
   self-contradictory request) and not something I found a reason to
   special-case away.

NOTHING FOUND OUT OF SCOPE requiring a new ticket filing.

Worktree: /home/logan/projects/frob/.claude/worktrees/t-4524
Branch: t-4524
Commit: fb7ba0468
git -C <worktree> status --short: empty
git -C /home/logan/projects/frob status --short: empty

READY

FOLLOW-UP (land refusal, ARCH001)

frob ticket land refused with: "src/frob/app/check_runner.py:1552
check_runner.py::run is now 68 line(s), past ARCH001's long-AND-complex
threshold ... split the function".

Fix: git merge dev --no-edit in the worktree (reported "Already up to
date" -- dev had not diverged from this worktree's base at merge time).
Split run() into three functions, zero behavior change:
  - _resolve_check_root(cfg) -> Path: the root.exists() check plus the
    --skip/--only conflict check, previously inline in run().
  - _handle_lease_and_stamp_modes(root, cfg) -> bool: the ticket-lease
    mismatch + --stamp-* early-exit handling block, previously inline
    in run() (docstring carries forward the existing T-0806/T-2486
    rationale comments verbatim).
  - run() now calls both and is ~34 lines (was 68).

Verified: ruff check / ruff format --check / ty check on
src/frob/app/check_runner.py all clean. Serial pytest:
  PYTHONPATH=<WT>/src python -m pytest -q -p no:cacheprovider -p no:xdist
    tests/unit/test_check_skip_flag.py tests/test_check_runner.py
  -> 49 passed, exitstatus=0

Commit: f2c5424a6 "refactor(check): split run() to clear ARCH001 length
threshold"
git -C <worktree> status --short: empty
git -C /home/logan/projects/frob status --short: empty

READY (post-split)

### Changed
```
 docs/commands/check.md             |  71 ++++++----
 src/frob/_cli_parsers/__init__.py  |   2 +
 src/frob/_cli_parsers/_check.py    | 279 +++++++++++++++++++++++++++++++++----
 src/frob/app/check_runner.py       |  97 +++++++++----
 tests/unit/test_check_skip_flag.py | 192 +++++++++++++++++++++++++
 tickets/T-4524/done-report.md      | 176 +++++++++++++++++++++++
 tickets/T-4524/ticket.md           |  15 +-
 7 files changed, 750 insertions(+), 82 deletions(-)
```

### Evidence
- `tests/unit/test_check_skip_flag.py::TestUnifiedSkipFlag::test_comma_split_sets_both_legacy_attributes` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_skip_flag.py::TestLegacyFlagsDeprecated::test_legacy_flag_still_works` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_skip_flag.py::TestSkipOnlyConflict::test_conflicting_stage_detected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 41 error(s), 4961 warning(s), 980 waived
- error-findings: AFFECT001@src/frob/_cli_parsers/_check.py, AFFECT001@src/frob/app/check_runner.py, ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, COV001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@design/frob.strata, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@src/frob/__main__.py, CROSSTICKET001@src/frob/_cli_parsers/_ticket/_progress.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/config.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/dup/_legacy_cs.py, CROSSTICKET001@src/frob/gates/__init__.py, CROSSTICKET001@src/frob/tickets/_land.py, CROSSTICKET001@src/frob/tickets/_leases.py, CROSSTICKET001@tests/unit/test_check_scoped_files.py, DOC004@docs/commands/check.md, DOC005@docs/modules/cli.md, DUP001@src/frob/_cli_parsers/_check.py, DUP001@src/frob/app/check_runner.py, DUP001@tests/unit/test_check_skip_flag.py, MILE001@tickets.md, OPAQUE001@src/frob/_cli_parsers/_check.py, OPAQUE001@src/frob/app/check_runner.py, PERF004@src/frob/_cli_parsers/_check.py, PERF004@src/frob/doctor.py, PRE001@tickets/T-4524, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, TEST001@src/frob/_cli_parsers/_check.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-3232.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4512.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4517.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4520.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4543.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4550.json, WIRE001@src/frob/_cli_parsers/_check.py, WIRE002@src/frob/dup/_legacy_cs.py, invalid-argument-type@tests/unit/test_ticket_runner_land_cmd_flags.py, unresolved-attribute@tests/unit/test_land_stackdump.py
