## Done report

MEASURED twice independently (T-3277's landing, 2026-08-28; the T-2667
landing series' "Series EJ" incident, 2026-08-29): `frob ticket close`
reported success on a ticket that `frob ticket land` then refused as
NotCloseable. Root cause (defect 1, the code-level mechanism the
second incident named directly): `_done_transition_structural_guard`
(src/frob/tickets/_evidence.py) downgraded a missing evidence/Done-
report state to a WARN + rapid-debt line under `rapid=True`, letting
close succeed -- but `land`'s own NotCloseable gate
(`_land_merge.py`: `if not ticket.evidence or not _has_done_report(...)`)
requires BOTH unconditionally, with no profile parameter to relax by.
Close and land disagreed about what "closeable" means.

Fix (per this ticket's own explicit instruction: do not loosen land's
check): close now refuses UNCONDITIONALLY for this one condition, same
`MissingEvidence` outcome and wording the non-rapid path already used,
regardless of profile. `rapid` still governs the SEPARATE, deliberately
narrower hollow-report exemption (T-3195) immediately below it --
unchanged.

DECISION on the ticket's stated design question (should a no-
behaviour-change ticket be required to cite pytest evidence at all):
YES. Land's gate makes no narrative exception and "do not loosen
land's check" forecloses adding one to close either, so the honest fix
is to require it consistently rather than reopen the divergence. The
accepted cost (binding an adjacent real test even for an accounting-
only change, as the T-2667 series' own workaround did by hand) is
smaller than trusting a close-time declaration, which is precisely the
trust boundary land's evidence check exists to enforce. A genuinely
evidence-free close still has its dedicated, visible escape hatch
(DOCS-kind rapid, or a `cmd:` evidence entry -- land's own error text
already names this remedy).

Two pre-existing tests (`test_docs_kind_rapid_hollow_report_exempt`,
`test_no_behaviour_change_narrative_exempt`) asserted the OLD
behavior with `evidence=()` -- both were themselves a THIRD latent
instance of this exact divergence (a close that would succeed today
with zero evidence, then be refused by land's own unconditional
evidence requirement, completely independent of the hollow-report
question). Updated both to bind real/`cmd:` evidence, matching land's
own documented remedy for a docs-kind ticket.

Fixtures (tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency):
- test_rapid_missing_evidence_and_done_report_still_refuses (MUST-FIRE,
  renamed in place from the old leniency test, assertion inverted):
  refused at close time under rapid, same wording/outcome land uses.
- test_non_rapid_missing_evidence_and_done_report_still_refuses
  (MUST-STILL-PASS CONTROL): unchanged non-rapid refusal.
- test_rapid_with_real_evidence_and_done_report_lands_without_extra_steps
  (MUST-STAY-QUIET): a normal close with real evidence/report proceeds
  exactly as before.

T-1585's own evidence citation (the archived ticket that introduced
the now-removed leniency) named the renamed test's OLD id --
rebound via `frob ticket evidence T-1585 --archived --replace ...`
rather than left orphaned.

OUT OF SCOPE, both explicitly deferred and filed as a follow-up
(T-3468): defect 2 (`done-report` does not mirror a worktree
write to the primary checkout like `body`/`evidence`/`new`, so the
ticket body's THIRD FIXTURE is not covered by this fix) and defect 3
(the `body --append` "## Done report" heading-collision with land's
gate). Neither's code lives in this ticket's declared scope
(src/frob/tickets/_done_report.py); the real defect-1 fix required
scope-adding src/frob/tickets/_evidence.py (reasoned via `frob ticket
scope --reason`), and defects 2/3 live in the CLI dispatch layer/
_reporting.py, a materially larger surface this fix does not carry.

Tests run: tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency,
TestHollowDoneReportGuard, TestStaleClaimsGuard (12/12 pass); full
tests/test_tickets.py (204/204 pass); tests/unit/test_close_rel001_bump.py
+ tests/unit/test_ticket_runner_gate_findings.py (55/55 pass).

### Changed
```
 tickets/T-3336/ticket.md           | 107 ++++++++++++++++++++++++++++++++++++-
 tickets/T-3468/ticket.md |  67 +++++++++++++++++++++++
 tickets/archive/T-1585/ticket.md   |  12 ++++-
 3 files changed, 184 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_missing_evidence_and_done_report_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_non_rapid_missing_evidence_and_done_report_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestDoneTransitionStructuralGuardRapidLeniency::test_rapid_with_real_evidence_and_done_report_lands_without_extra_steps` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 14 error(s), 4244 warning(s), 864 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
