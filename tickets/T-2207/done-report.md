## Done report

Fixed both halves of the identity-less quarantine finding defect.

PRODUCER (src/frob/verify/_quarantine.py::raise_quarantine): before
persisting, filters out any finding whose rule_id AND file are both
empty (a new _is_unidentifiable helper), logging at ERROR. A batch with
only identity-less findings now returns Err(EmptyFindings) instead of
writing garbage to disk.

CONSUMER (src/frob/verify/_quarantine.py::retire_unidentifiable_findings,
new public function): retires every identity-less finding in the
currently-raised record by dismissing it with the caller's reason/actor,
then applies clear_quarantine's own "clear only if every finding is
disposed" rule. A well-formed undisposed sibling still blocks the actual
clear -- confirmed by test_retire_unidentifiable_findings_still_blocks_
on_a_well_formed_sibling, which retires the identity-less record, checks
the clear is still refused (FindingsNotDisposed), then disposes the real
finding via the normal clear_quarantine path and confirms that clears.
This exists because the CLI's RULE:FILE:LINE dispose addressing
(frob.app.verify_runner._parse_finding_arg) structurally can never key
to ("", "", None) -- an empty file component is always rejected as
malformed -- confirmed directly in
test_cli_addressing_can_never_key_an_identity_less_finding.

Repro: test_retire_unidentifiable_findings_recovers_a_stuck_store
committed alone at 138dac72e, confirmed FAILED_AT_PARENT via
`frob ticket evidence --check-repro ... --base-ref 138dac72e`
(ImportError on the not-yet-existing retire_unidentifiable_findings).
Fix committed separately at 5a2ee37e7.

Cut: CLI wiring (`frob verify dispose --retire-unidentifiable`) is not
included -- src/frob/app/verify_runner.py is outside this ticket's
declared scope (src/frob/verify/_quarantine.py only). The recovery verb
is usable directly (frob.verify._quarantine.retire_unidentifiable_
findings) and is the right shape for a CLI wrapper; filed as a follow-up.

Tests: 22 passed in tests/unit/verify/test_quarantine.py (was 15 before
this ticket), `uv run pytest tests/unit/verify/test_quarantine.py
-o addopts="" -q` -- "22 passed in 0.20s". Touched-set `frob test --base
main` python suite: exit=0, 13 outcomes recorded.
Static check (`frob check --only static --json`): 3 errors, all
pre-existing import cycles unrelated to this file (gates/_docblocks*,
dup/_pipeline/*, tickets/_land_*).

### Changed
```
 docs/modules/tickets-verify-sweep.md |  34 ++++++++
 frob.lock                            |  88 +++++++++++++++++++
 src/frob/verify/_quarantine.py       | 165 +++++++++++++++++++++++++++++++++++
 tests/unit/verify/test_quarantine.py | 158 +++++++++++++++++++++++++++++++++
 tickets/T-2207/done-report.md        |  67 ++++++++++++++
 tickets/T-2207/ticket.md             |  60 +++++++++++--
 tickets/T-2217/ticket.md   |  34 ++++++++
 7 files changed, 601 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_cli_addressing_can_never_key_an_identity_less_finding` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_retire_unidentifiable_findings_recovers_a_stuck_store` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_retire_unidentifiable_findings_still_blocks_on_a_well_formed_sibling` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_retire_unidentifiable_findings_refuses_when_none_present` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_retire_unidentifiable_findings_refuses_when_not_raised` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_raise_quarantine_drops_identity_less_findings_at_write_time` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIdentityLessFindingRecovery::test_raise_quarantine_refuses_when_only_identity_less_findings_given` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2207/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
