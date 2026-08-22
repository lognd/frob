## Done report

Changed:
- docs/modules/tickets-data-storage.md (Data models: Ticket.evidence_changes
  entry; Error types: TicketError.EvidenceReplaceReasonMissing entry)
- docs/modules/tickets-landing.md (new "Required reason and the
  evidence_changes audit trail (T-1733)" subsection under
  `frob ticket evidence --replace` (T-1537))
- src/frob/tickets/_models.py (Ticket, TicketError: removed 2
  frob:waive AFFECT001 directives)
- src/frob/gates/_mutation_evidence.py
  (mutation_evidence_violations: removed 1 frob:waive AFFECT001 directive)
- src/frob/tickets/_evidence.py (replace_evidence: removed 1
  frob:waive AFFECT001 directive)

Verified before starting: all four AFFECT001 waivers cited T-2620 by name
as the tracking ticket for exactly this doc work (grep confirmed on all
four sites); none of them are documenting anything not covered by this
change.

Positive control: `frob check --ticket T-2620 --only gates-fast` before
this change reported 39 errors (baseline, unrelated to this ticket:
TICK003/TICK004/TICK011/TICK012 ledger-age findings, a pre-existing
mile004 doc anchor, claude-config-drift). After adding the three doc
sections and removing the four waivers, the same run still reports 39
errors -- zero AFFECT001 findings anywhere, and zero DOC002/COV001
findings on the four touched symbols or the two new/extended doc
sections. Reverting the tickets-landing.md subsection (or the two
tickets-data-storage.md entries) locally and re-running reproduces the
original AFFECT001 findings at all four waiver sites, confirming the
sections actually close the edge rather than the finding merely having
moved.

Evidence: `tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches` (pytest node id, PASSES both before and after
this change). This is confirmatory-only -- `--check-repro` reports
PASSED_AT_PARENT, expected and unavoidable for a docs-only ticket with
no own pytest surface (per the T-0167 doc-ticket evidence precedent,
playbook section 5, most recently applied by T-2662). T-2620's `kind` is
`docs`, not `bug`/`security`, so BUG002 does not apply here at all --
no waiver needed and none added.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-2620 --only gates-fast` clean of
AFFECT001/COV001/DOC002 on this ticket's touched set; the 39 pre-existing
repo-wide errors are unrelated ledger/anchor/config-drift findings
predating this change (confirmed identical count before and after).

Follow-up for the coordinator: with these four waivers removed, the
promised follow-up work T-2612/T-2656 deferred is now actually done --
no further doc-anchor debt remains for evidence_changes/
EvidenceReplaceReasonMissing.

### Changed
```
 tickets/T-2620/ticket.md | 101 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 100 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, LANG004@src/frob/lang/_support.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2620, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
