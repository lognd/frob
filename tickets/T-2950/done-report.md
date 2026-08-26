## Done report

Changed:
- src/frob/app/status_runner.py (FindingsMovement/StatusReport docstrings updated;
  run() now gates ticket-flow mining on cfg.status_tickets, default False;
  _print_status_human's ticket-movement "not measured" message names --tickets)
- src/frob/_cli_parsers/_status.py (added --tickets opt-in flag; --no-tickets kept
  as deprecated no-op)
- src/frob/app/config.py (added status_tickets: bool = False; status_no_tickets
  kept as deprecated no-op field)
- src/frob/app/_config_external.py (status_tickets added to the bool forwarding list)
- tests/test_status.py (updated CLI-parser tests for --tickets/--no-tickets; added
  TestRunEndToEnd.test_default_cfg_skips_ticket_flow_and_says_so)
- docs/modules/cli.md (frob status section rewritten: ticket movement is opt-in,
  default fast path documented, --no-tickets marked deprecated)

Root cause (measured, not guessed): frob.tickets.ticket_flow's landed-per-day
mining calls _mine_done_transitions over EVERY ticket id (active tickets merged
with tickets-archive.md's archived tickets via _load_flow_ticket_universe). In
v2-store mode this dispatches to _mine_done_transitions_v2, which for every
single ticket id spawns two git subprocesses (a rename-lineage check via
_v2_rename_source, plus a full `git log --reverse -p` walk via
_mine_v2_path_transitions). Isolated this worktree's ledger (137 active +
~1000 archived tickets after the day's archive sweep) and timed the section in
isolation: _flow_section alone took 313.2s of the observed 341s frob-status
wall clock (findings section 0.34s, verify section 0.18s) -- process-spawn
overhead across ~2000 git subprocess calls, not a single hot loop. The other
two sections were already reused-artifact reads and were never the bottleneck.

Fix: made the ticket-movement section opt-in (T-2950's own sanctioned "make it
optional and off by default" path, since the per-ticket subprocess-spawn cost
is structural to how git history is mined and not fixable without a larger
caching project outside this ticket's scope). Default `frob status` now skips
ticket_flow entirely and reports the section as an explicit "not measured:
ticket-flow mining is off by default ... pass --tickets to include it" --
never a silent omission, matching the stale-baseline honesty voice already in
this module. `--tickets` opts back in for anyone who wants the movement
numbers and can afford the multi-minute wait on a large/old repo.
`--no-tickets` is kept as a deprecated no-op so a script/CI job that already
passes it does not break.

Wall-clock, measured:
- BEFORE (as given in the ticket, this session's own measurement): real 5m41.500s
  user 3m52.435s sys 1m43.954s
- AFTER, bare `frob status` in this worktree: real 0m0.605s user 0m0.517s
  sys 0m0.090s (also re-measured at 0m0.543s on a second run)
- Isolated confirmation that the removed default cost really was the
  bottleneck: _flow_section alone measured 313.2s (5m13.3s wall) in this same
  worktree/ledger, out of a 341s three-section total -- i.e. >91% of the
  original 5m41s was the section now made opt-in.

Honesty behaviour proof:
- Unit tests (all passing, see Evidence) directly assert the no-fabrication
  contract: TestComputeFindingsMovement.test_must_not_invent_missing_baseline
  and the stale-baseline variant continue to return measured=False with an
  explicit reason and every count left None (never coerced to 0) -- this
  logic was untouched by this change, and its tests still pass.
- New test TestRunEndToEnd.test_default_cfg_skips_ticket_flow_and_says_so
  asserts a bare AppConfig (status_tickets defaults False) still prints
  "== ticket movement ==" plus the explicit "not measured: ticket-flow
  mining is off by default ... --tickets" text -- never a blank/omitted
  section and never a fabricated zero.
- TestBuildStatusReportIntegration.test_stamped_baseline_with_no_tree_change_is_a_real_zero
  still passes: a genuine zero-movement measurement (net=0, not a refusal)
  renders as measured=True with real healed/introduced/net=0 -- confirms a
  real "nothing changed" result is never confused with "not measured".

Filed: none -- this ticket's own scope covered the whole fix; no out-of-scope
discovery this pass.

Gates: `frob check --ticket T-2950` clean for every file in this ticket's
scope (zero SCOPE001/COV002/COV001/TEST001 findings against
status_runner.py, _status.py, config.py, _config_external.py,
tests/test_status.py, docs/modules/cli.md); repo-wide gate-summary read 28
errors/533 warnings, all pre-existing and unrelated to this ticket's files
(verified via gate:scope-note's own caveat plus per-file diagnostic
filtering of the JSON output).

### Changed
```
 docs/modules/cli.md              | 36 ++++++++++++-------
 src/frob/_cli_parsers/_status.py | 16 +++++++--
 src/frob/app/_config_external.py |  2 ++
 src/frob/app/config.py           | 14 ++++++--
 src/frob/app/status_runner.py    | 26 ++++++++++++--
 tests/test_status.py             | 35 +++++++++++++++---
 tickets/T-2950/ticket.md         | 77 +++++++++++++++++++++++++++++++++++++++-
 7 files changed, 182 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_status.py::TestComputeFindingsMovement::test_must_not_invent_missing_baseline` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestBuildStatusReportIntegration::test_no_baseline_reports_unmeasured_findings` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestBuildStatusReportIntegration::test_stamped_baseline_with_no_tree_change_is_a_real_zero` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestRunEndToEnd::test_run_prints_human_text_by_default` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestRunEndToEnd::test_run_prints_json_when_requested` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestRunEndToEnd::test_default_cfg_skips_ticket_flow_and_says_so` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestAddStatusParser::test_registers_status_subcommand_with_expected_flags` (pytest node id, verified passing when recorded)
- `tests/test_status.py::TestAddStatusParser::test_bare_status_has_no_op_defaults` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 24 error(s), 533 warning(s), 855 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, PRE001@tickets/T-2950, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
