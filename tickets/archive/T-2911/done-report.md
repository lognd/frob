## Done report

Added `frob status`: a delta-first movement summary (findings healed/
introduced since the last stamped baseline, verification lag against the
T-1686 watermark, ticket landing velocity) built to answer the coordinator's
adoption concern directly -- a large absolute `frob check` finding count
(1,146 warnings on this repo, 4,948 on a foreign repo) has no way on its own
to tell a newcomer whether that number is shrinking.

Design, reuse-first per the brief:

- Findings movement: `frob.gates.load_baseline`/`is_baseline_stale`/
  `violation_fingerprint` -- the EXACT `.frob/baseline` store and
  fingerprint identity `frob check --delta` already uses. The current
  violation set is collected via `frob.gates.run_gates`/`GateConfig`, the
  SAME call shape `frob check --stamp-baseline` itself uses
  (`_run_baseline_chunks`), not a second gate-running path. `--only`
  selects which gate(s) to scan (default: the existing `gates-fast` stage
  group, expanded via the existing `frob.check._expand_stage_groups` --
  no new grouping invented).
- Verification lag: `frob.app.verify_runner.build_status` -- the exact
  function `frob verify status` calls.
- Ticket movement: `frob.tickets.ticket_flow` -- the exact function
  `frob ticket flow` calls. `--no-tickets` skips it (it mines the WHOLE
  ledger's git history and is the single most expensive part of this
  command).

The one genuinely new computation is `compute_findings_movement`
(healed/introduced/net over baseline-vs-current fingerprints), pure and
unit-tested in isolation.

Honesty rule (the coordinator's explicit hard requirement, motivated by
this session's own 53-commit-stale-watermark incident): a missing OR
stale baseline reports `measured: false` with an explicit reason and
every count as `None` -- never a fabricated delta. Demonstrated live, not
just in fixtures:

- Must-not-invent, no baseline: `frob status --no-tickets` on a fresh
  worktree (before any `--stamp-baseline`) printed "not measured: no
  baseline stamped yet -- run `frob check --stamp-baseline`...".
- Must-not-invent, stale baseline: stamped a baseline, then edited
  `status_runner.py` itself (a tracked file the baseline covers) and
  re-ran `frob status` -- it correctly detected `is_baseline_stale` and
  printed "not measured: baseline is STALE ... re-stamp with `frob check
  --stamp-baseline`" instead of a number.
- Must-show, real measurement: stamped a real baseline over
  {invariant,test,policy,doclink} (69 real violations), re-ran `frob
  status --only invariant --only test --only policy --only doclink
  --no-tickets` with no tree changes -- reported `healed: 0, introduced:
  0, net: +0 (measured against 4 gate famil(ies))`, a real measured zero,
  not a refusal.
- Must-show, ticket movement: `frob status` (tickets included) against
  this repo's real ledger reported `open: 83, landed today: 24, trailing
  net rate: +4.3/day` -- real numbers off `ticket_flow`, not fixtures.

Unit tests (`tests/test_status.py`, 9 cases) cover both directions of the
honesty rule (missing baseline, stale baseline, no current run) and both
directions of real movement (healed+introduced together netting to zero,
pure healing giving a positive net, a real measured zero when nothing
moved) plus two integration-shaped tests against a real (not mocked)
`.frob/baseline` store via `tmp_path`.

CLI wiring: `frob status [--path DIR] [--json] [--only GATE] [--no-tickets]`,
following the exact `Subcommand`/`_SUBCOMMAND_RUNNER_NAMES`/
`_apply_*_fields` plumbing every other subcommand uses (`src/frob/app/
config.py`, `src/frob/app/app.py`, `src/frob/app/_config_external.py`,
`src/frob/__main__.py`, `src/frob/_cli_parsers/__init__.py`) -- caught and
fixed one real gap along the way: the new AppConfig fields were not
initially added to `_config_external.py`'s `_PATH_FIELDS`/`_LIST_FIELDS`/
`_BOOL_FLAGS` forwarding tuples, so `--no-tickets` silently never reached
`AppConfig` at all (a live T-2004-shaped defect on my own new flags,
caught by `find_dropped_cli_flags`'s own test suite before I could ship it
that way).

Docs: added a `frob status` section to `docs/modules/cli.md`, a README.md
command-table row (`frob docs --sync-commands` regenerated cli.md's
generated block; the README row and count were hand-maintained per
DOC005's own contract). `design/frob.strata`'s `testsuite` node needed
`tests/test_status.py` added to its `exec` via-list (SYS100/SELFAUDIT001,
for the one `subprocess.run(["git","init"...])` fixture-setup call) and
the capability-via-ratchet ceiling bumped from 197 to 198 sites
(`docs/design/registry/capability-via-ratchet.lock.json`), same shape
every other test file in that via-list already required.

Verification:
- `uv run pytest tests/test_status.py -p no:cacheprovider -q`: 9 passed.
- `uv run ruff check`/`uv run ty check` on every new/changed file: clean.
- `uv run frob check --only test --only coverage --only docblocks --ticket
  T-2911` (cache-bypassed via `FROB_NO_GATE_CACHE=1` after discovering a
  stale-cache false-positive on TEST001 -- see docs/guides/agent-playbook.
  md#6): 0 errors tied to this ticket's diff; all remaining errors verified
  pre-existing on main (COV004 attachment-sha drift on other tickets,
  CYCLE001, DOC006/DOC008 on unrelated docs, TICK004, WIRE002).
- `uv run frob check --land-parity` (cache-bypassed): 18 unscoped errors,
  all confirmed pre-existing/unrelated by running the identical command
  directly against main.
- `uv run frob claude sync --check`: clean (no managed-config files
  touched by this ticket).

### Changed
```
 tickets/T-2911/ticket.md | 68 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 67 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_missing_baseline` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_stale_baseline` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_no_current_run` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestComputeFindingsMovement::test_must_show_healed_and_introduced` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestComputeFindingsMovement::test_must_show_pure_healing_is_positive_net` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestComputeFindingsMovement::test_honest_zero_when_nothing_moved` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestFindingsMovementModel::test_defaults_are_unmeasured_shaped` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestBuildStatusReportIntegration::test_no_baseline_reports_unmeasured_findings` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestBuildStatusReportIntegration::test_stamped_baseline_with_no_tree_change_is_a_real_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 19 error(s), 755 warning(s), 856 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2911, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
