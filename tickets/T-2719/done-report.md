## Done report

Changed:
- src/frob/gates/_render_lint.py::_EXEMPT_PREFIXES (was `_EXEMPT_PREFIX`, single string; now a
  tuple: `src/frob/render/`, `.claude/hooks/`, `scripts/fleet_status.py`)
- src/frob/gates/_render_lint.py::_EXTRA_SCAN_PATHSPECS (new)
- src/frob/gates/_render_lint.py::_tracked_python_files (now unions `src/frob` with
  `_EXTRA_SCAN_PATHSPECS`, de-duplicated)
- src/frob/gates/_render_lint.py::render_lint_gate (docstring updated; exemption check now
  `rel_path.startswith(_EXEMPT_PREFIXES)`)
- tests/test_gates.py::TestRenderLintGate.test_claude_hooks_dir_exempt (new)
- tests/test_gates.py::TestRenderLintGate.test_fleet_status_file_exempt (new)
- tests/test_gates.py::TestRenderLintGate.test_exemption_is_file_scoped_not_dir_scoped (new)
- docs/modules/render.md (Renderer section: documents the widened scan + exemption prefixes;
  added to scope via `frob ticket scope --add` to satisfy AFFECT001, which fired because
  render_lint_gate's affects()-closure names this doc)

Root-cause finding disclosed up front: measured directly (calling `render_lint_gate` against
this repo, and via `frob check --only render_lint --no-cache`) that BEFORE this fix, RENDER001
did not scan `.claude/hooks/**` or `scripts/fleet_status.py` at all -- the default pathspec
passed to `tracked_python_files_for_gate` was `src/frob` only. The 11 `frob:waive RENDER001`
directives T-1614's audit found in those files were therefore not suppressing any live finding;
they were latent/inert. The fix does two things together, not one:
1. widens the RENDER001 scan to include `.claude/hooks/**/*.py` and the single file
   `scripts/fleet_status.py` (so the exemption is a real, testable no-op instead of dead code
   that merely never runs, and so a NON-exempt file added under either path is caught rather
   than silently invisible), and
2. extends `_EXEMPT_PREFIXES` to cover exactly those same two paths.

Net effect on current findings: unchanged (0 before, 0 after, in `.claude/hooks/` and
`scripts/fleet_status.py`) -- but now for a real, measured reason (exempt) rather than an
accidental one (unscanned).

Both-direction proof (T-2723's `--no-cache` caution followed for every measurement below):

- False positive stops firing: `render_lint_gate` measured against the real repo tree with
  `_EXEMPT_PREFIXES` temporarily monkeypatched back to `("src/frob/render/",)` (exemption
  removed, scan left widened) produces 28 RENDER001 violations across
  `.claude/hooks/{diagnosis-nudge,frob-suggest,frob-timeout-guard,pending-background-guard,
  root-cleanliness-detector,root-write-guard,sync-claude-config}.py` and
  `scripts/fleet_status.py`. With `_EXEMPT_PREFIXES` restored (the actual fix), those same 28
  drop to 0 -- confirmed via `frob check --only render_lint --no-cache --json` read through
  `scripts/check_summary.py` (never grep), both before and after the code change: 4 RENDER001
  errors both times, all four in `src/frob/release/_cli.py` (pre-existing, out of scope),
  zero in `.claude/hooks/` or `scripts/fleet_status.py` either time.
- Genuine violation still fires (must-still-fire control, real fixture not prose):
  `test_bare_print_fires` (pre-existing, unmodified) still passes -- a bare `print` in
  `src/frob/app/offender_runner.py`-shaped fixture still fires RENDER001.
  `test_exemption_is_file_scoped_not_dir_scoped` (new) directly asserts
  `"scripts/bump_version.py".startswith(_EXEMPT_PREFIXES)` is False and
  `"scripts/other_tool.py".startswith(_EXEMPT_PREFIXES)` is False, proving the
  `scripts/fleet_status.py` exemption is a single named file, never a `scripts/` directory
  prefix -- a sibling script that genuinely imports `frob.*` (e.g. `bump_version.py`) stays
  fully subject to RENDER001. (A gate-level "still fires" fixture for `scripts/other_tool.py`
  would prove nothing: `scripts/` generally is deliberately NOT one of the added scan
  pathspecs -- only the one named `scripts/fleet_status.py` file was added -- so widening the
  scan to cover a hypothetical sibling script was rejected: those other `scripts/*.py` files
  (`bump_version.py`, `check_summary.py`, `verify_lands.py`) have zero existing RENDER001
  waivers and DO import `frob.*` in at least one case; scanning them would introduce brand-new,
  currently-un-triaged RENDER001 findings entirely outside this ticket's scope, which is exactly
  the kind of scope-widening a narrowing fix must not do as a side effect.)

Not done / disclosed cut: the 11 now-genuinely-redundant `frob:waive RENDER001` directives in
`.claude/hooks/*.py` and `scripts/fleet_status.py` were NOT removed -- those files are outside
this ticket's declared scope (`src/frob/gates/_render_lint.py`, `tests/test_gates.py`, plus
`docs/modules/render.md` added via `frob ticket scope --add` for AFFECT001), and the ticket's
own plan explicitly says not to remove them until the gate exemption exists on `main`. Filing
the follow-up cleanup ticket is the next step once this lands (see Filed below).

Filed: T-2733 (renumbers to a real id at land) -- "remove now-redundant
frob:waive RENDER001 directives in .claude/hooks and scripts/fleet_status.py now that T-2719's
directory/file exemption is live", scope `.claude/hooks/*.py`, `scripts/fleet_status.py`.
Note: `frob ticket new` reported this scope overlaps T-1945 (queued) and T-2691 (queued) on the
same files -- left as-is (not narrowed) since resolving that overlap is a follow-up-ticket
concern, not part of T-2719's own scope.

Evidence: tests/test_gates.py::TestRenderLintGate::test_bare_print_fires,
tests/test_gates.py::TestRenderLintGate::test_render_package_exempt,
tests/test_gates.py::TestRenderLintGate::test_stderr_directed_print_is_silent,
tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001,
tests/test_gates.py::TestRenderLintGate::test_claude_hooks_dir_exempt,
tests/test_gates.py::TestRenderLintGate::test_fleet_status_file_exempt,
tests/test_gates.py::TestRenderLintGate::test_exemption_is_file_scoped_not_dir_scoped,
tests/test_gates.py::TestRenderLintGate::test_scan_now_covers_hooks_and_fleet_status
(all 8 collected and passed: `pytest tests/test_gates.py -k TestRenderLintGate -q` ->
`SUITE-RESULT: exitstatus=0 collected=8 failed=0`)

BUG002 designated repro: test_scan_now_covers_hooks_and_fleet_status, `--check-repro`/
`--designate-repro --base-ref 679385a7a` (a test-only commit with the fix code NOT yet applied,
verified by diffing that commit's own `git show --stat`) reports FAILED_AT_PARENT -- confirmed
via an isolated `git worktree add --detach` checkout of that exact commit, run outside my own
worktree's live filesystem state (needed because pytest otherwise reads uncommitted working-tree
content, not the commit under test): `AssertionError: assert '.claude/hooks/some-hook.py' in
('src/frob/__init__.py',)`. The same test passes at HEAD (0c7234f87, the fix commit) as part of
the full 8/8 TestRenderLintGate pass above. `frob ticket evidence --designate-repro` itself
recorded FAILED_AT_PARENT and accepted the designation.

Gates: `frob check --ticket T-2719 --no-cache` clean of AFFECT001/PRE001/RENDER001 findings in
this ticket's own scope after adding the docs/modules/render.md scope + sweep re-run (remaining
errors in that run -- DRIFT001 x3, ARCH103, PERF00x, PII010/012, COV001/003/004, etc. -- are all
pre-existing, unrelated to this ticket's touched files/symbols, confirmed by file path).

### Changed
```
 docs/modules/render.md             |  22 ++++++++
 src/frob/gates/_render_lint.py     |  91 +++++++++++++++++++++++++-----
 tests/test_gates.py                | 104 ++++++++++++++++++++++++++++++++++
 tickets/T-2719/done-report.md      | 111 +++++++++++++++++++++++++++++++++++++
 tickets/T-2719/ticket.md           |  22 +++++++-
 tickets/T-2733/ticket.md |  30 ++++++++++
 6 files changed, 365 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestRenderLintGate::test_bare_print_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_render_package_exempt` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_stderr_directed_print_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_claude_hooks_dir_exempt` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_fleet_status_file_exempt` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_exemption_is_file_scoped_not_dir_scoped` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRenderLintGate::test_scan_now_covers_hooks_and_fleet_status` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 45 error(s), 1632 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2719-t2720/src/frob/_cli_parsers/_ticket/_closeout.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2719, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
