## Done report

secret-fake staleness now watched at the GATE level, respecting T-0157's reserved-verb constraint: fake_marker_staleness_gate re-scans reason-bearing marker sites and emits WAIVE004-rule findings when the site would no longer trip a real scanner absent the marker, folded into the same WAIVE004 stream as graph-edge waivers. Two empirical corrections: the marker family is shared with PII011 email fixtures (conservative plausibly-still-needed heuristic errs toward not-stale) and multi-line string-literal marker construction defeats line mapping (documented exclusion list per existing precedent). Zero false positives on a full-repo scan.

### Changed
```
 docs/modules/gates.md      |  19 ++++
 src/frob/gates/__init__.py |  15 ++-
 src/frob/gates/_secrets.py | 226 ++++++++++++++++++++++++++++++++++++++++++---
 tests/test_secrets_gate.py | 123 +++++++++++++++++++++++-
 tickets.md                 | 154 +++++++++++++++++++++++++++++-
 5 files changed, 520 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_stale_marker_fires_waive004` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_stale_marker_on_line_above_fires_waive004` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_live_marker_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_marker_discharging_email_shaped_pii_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_bare_marker_without_reason_is_not_a_staleness_site` (pytest node id, verified passing when recorded)
- `tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_docstring_style_mention_is_not_a_staleness_site` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
