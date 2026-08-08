## Done report

T-1855 implements the three remaining T-1848 items plus the sharpest
incident (scope --remove reporting success while changing nothing):

1. Grant-on-use for CrossTicketLeakage: `_leaked_hits_for_candidate` now
   downgrades a hit that matches ONLY via the implicit FEATURE-kind
   CLI-wiring grant to "not leaked" unless the sibling ticket has
   actually put that path to use (`_explicitly_used_wiring_path`, an
   audited `scope_changes` ADD entry overlapping the path). An unused
   blanket grant can no longer permanently reserve __main__.py/config.py/
   ticket_runner/__init__.py against every sibling's land.

2. `frob ticket show` disclosure: `_render_implicit_scope` appends an
   `implicit_scope: [...]` line naming any CLI-wiring file a FEATURE
   ticket effectively holds but never declared.

3. CrossTicketLeakage refusal disclosure: `_report_leaked_tickets` now
   annotates every leaked path with `_scope_claim_reason` ("declared" vs
   "implicit-cli-wiring") so the refusal names WHICH rule claimed the
   file.

4. `scope --remove` warning: `_mutate.py::_scope` now checks each removed
   glob against `_still_implicitly_covered` (ledger/own-shard/CLI-wiring
   rules) and WARNS loudly when the removal did not actually change the
   effective scope -- the exact T-1848 incident shape.

Full grant-on-use for the general `scope_matches()`/SCOPE001/PRE001
semantics (not just CrossTicketLeakage) needs `_models.py`, out of this
ticket's declared scope and not touched here -- filed as a follow-up
note in this Done report rather than silently expanded into.

AFFECT001 fired against `_check_cross_ticket_leakage`'s existing
docs/modules/tickets.md anchor; that file was leased to in-progress
T-1686 and could not be edited here. Waived with a reason citing the
lease conflict; follow-up draft filed (renumbers at land) to update the
anchor's prose once the file is free.

### Changed
```
 tickets/T-1855/ticket.md           | 40 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1860/ticket.md | 30 ++++++++++++++++++++++++++++
 2 files changed, 69 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_remove_still_implicit_warns` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_remove_genuinely_free_no_warning` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_declared_path_is_declared` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_implicit_cli_wiring_path_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_unused_implicit_grant_not_explicitly_used` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeClaimReasonAndGrantOnUse::test_explicit_add_counts_as_used` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_renders_implicit_cli_wiring_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets_acceptance.py::TestAcceptanceAmendmentsSurfaced::test_show_omits_implicit_scope_when_fully_declared` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 14 error(s), 868 warning(s), 743 waived
- error-findings: COV001@.claude/hooks/_shellscan.py, COV001@.claude/hooks/diagnosis-nudge.py, COV001@.claude/hooks/dispatch-telemetry.py, COV001@.claude/hooks/frob-suggest.py, COV001@.claude/hooks/frob-timeout-guard.py, COV001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, DOC003@docs/commands/sys.md, DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1855, SELFAUDIT001@design, TEST001@.claude/hooks/_shellscan.py, invalid-argument-type@src/frob/strata/_sync_may.py, invalid-type-form@src/frob/strata/_sync_may.py
