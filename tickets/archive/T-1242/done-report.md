## Done report

Added the exposure:public-web attr vocabulary and a PRIVACY-NOTICE
RegulationEntry to std.compliance so a public-web-exposed Pii-or-above
node with no declared privacy-policy mitigation fails the compliance
gate.

Changed:
- src/frob/strata/_compliance.py: _EXPOSURE_PREFIX/_PRIVACY_POLICY_ATTR
  constants, _has_exposure helper, PRIVACY-NOTICE RegulationEntry (cite
  GDPR art.13, see-also CCPA Sec.1798.100), _check_privacy_notice +
  _privacy_notice_node_violations (node-level check mirroring
  _check_baa's flow-level shape, with Claim-override support via the
  existing _claim_override helper), wired into check_regulation_discharge.
  Module docstring updated with the new attr vocabulary.
- tests/unit/strata/test_compliance.py: TestPrivacyNotice (3 tests --
  fires with no mitigation, discharges with the privacy-policy attr,
  silent when exposure:public-web is absent).
- docs/strata/threat.md#compliance: new obligation table row.
- docs/design/compliance-corpus.md: catalog table + count bumped 6 -> 7.
- docs/guides/extending/compliance-registry.md: entry count and
  discharge-function list updated.

Gates: `uv run frob check --only scope --only prework --ticket T-1242`
clean (0 errors; 119 pre-existing warnings from _models.py/_pii.py/
_threat.py/_audit.py doc-anchor cross-refs already in scope before this
ticket, unrelated to this change). `uv run frob check --only gates-fast
--ticket T-1242`: only pre-existing DEPR002 (stale T-0802 deprecation
directives) and DOC001 (pre-existing orphan docs) errors remain, both
unrelated to this ticket's files.

Scope was widened via `frob ticket scope T-1242 --add
tests/unit/strata/test_compliance.py --add
docs/design/compliance-corpus.md` (both named in the ticket's own
instructions) and re-swept.

Evidence: tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_public_web_node_with_no_mitigation_refutes,
tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_declared_privacy_policy_attr_discharges,
tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_no_public_web_exposure_is_silent
(bound to acceptance indices 0/1/2). Full file: `uv run pytest
tests/unit/strata/test_compliance.py -p no:cacheprovider -q` -> 42
passed (39 pre-existing + 3 new).

Filed: none -- docs/design/registry/compliance.yaml's
CMPL-FROB-CATALOG-ENTRIES leaf_count (6) is now stale against
COMPLIANCE_CATALOG's real count (7); it is outside this ticket's
declared scope and no gate checks that arithmetic today (grep confirmed
no code reads total_leaf_controls_enumerated), so left as a known,
disclosed cosmetic drift rather than expanding scope -- worth a one-line
fix whenever that yaml is next touched (e.g. as part of T-1244's
sibling COMPLIANCE005/registry work).

### Changed
```
 tickets.md | 31 ++++++++++++++++++++++++++-----
 1 file changed, 26 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_public_web_node_with_no_mitigation_refutes` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_declared_privacy_policy_attr_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_no_public_web_exposure_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 9 error(s), 436 warning(s), 674 waived
- error-findings: DEPR002@src/frob/app/docs_runner.py, DEPR002@src/frob/app/map_runner.py, DEPR002@src/frob/app/outline_runner.py, DEPR002@src/frob/app/xref_runner.py, DOC001@docs/audits/docs-staleness-2026-07-29.md, DOC001@docs/design/check-fix-engine.md, DOC001@docs/design/ledger-v2.md, DOC001@docs/design/refactor-verb.md, SELFAUDIT001@design
