## Done report

Changed:
  src/frob/gates/_pii_structural/_keywords.py::_PII012_REVIEWED_NON_PII (added 3 new (file, identifier) entries)
  tests/test_pii_structural_gate.py::TestKeywordSweep (2 new regression tests)

Verified before waiving (Series EL's earlier triage was NOT confirmed -- did that here): all
four PII012 findings were checked at their actual call sites, not assumed:

  - src/frob/app/doctor_runner.py:64 `run_diagnosis` -- frob's own doctor/health-check entry
    point (`frob.doctor.run_diagnosis`, `frob doctor` CLI), never a medical diagnosis.
  - src/frob/serve/_socketd.py:756 `allow_reuse_address` -- `socketserver.BaseServer`'s
    `SO_REUSEADDR` class attribute (a unix-socket bind option), never a postal/contact address.
  - tests/unit/test_doctor_runner_t1276.py:142,170 `_run_diagnosis_records_levels` -- a local
    test double for the same `run_diagnosis` symbol above.

Both ARE genuine false positives, same class T-2069 already fixed for "token": an ordinary
English word doubling as this codebase's own domain vocabulary. Standing directive (checks
must compare SYMBOLS, not lexical text) is why the fix uses the detector's own EXACT (file,
identifier-text) allowlist (`_PII012_REVIEWED_NON_PII`, T-0540's established per-site review
mechanism), not four `frob:waive PII012` comments and not a blanket keyword-wide change. Two
new tests (`test_reviewed_non_pii_diagnosis_homonym_stays_quiet_at_its_site`,
`test_reviewed_non_pii_address_homonym_stays_quiet_at_its_site`) prove the exemption is exact:
the same identifier at an unreviewed site still fires.

Evidence:
  frob check --only pii_structural (repo-wide): gate:PII 0 errors (was 4)
  tests/test_pii_structural_gate.py: 132/132 pass (130 pre-existing + 2 new)
  frob check --ticket T-3390: gate:PII clean for this ticket's scope

Filed: none (no out-of-scope work found)
Gates: frob check --ticket T-3390 -- gate:PII clean; remaining FAIL rows in the ticket-scoped
  summary (CYCLE001, DEPR006, DOC003/DOC011, LARGE001, LEXCHECK001, OPAQUE001, PERF004, REL001,
  SELFAUDIT001, TICK004, WAIVE011) are pre-existing repo-wide findings outside T-3390's scope,
  not introduced by this change; verified by re-measuring gate:PII in isolation above.

### Changed
```
 tickets/T-3390/ticket.md | 12 +++++++++++-
 1 file changed, 11 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_reviewed_non_pii_diagnosis_homonym_stays_quiet_at_its_site` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_reviewed_non_pii_address_homonym_stays_quiet_at_its_site` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 21 error(s), 4316 warning(s), 896 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC011@docs/modules/tickets.md, LARGE001@src/frob/__main__.py, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
