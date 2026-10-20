+++
id = "01M38BCNB38AS6RM0RGZ1BEP28"
title = "WEBSEC120 positive fixture fires zero findings (webapp-owned)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "agent"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5475"]
labels = ["milestone:v0.534.0"]
scope = ["src/frob/webapp/_websec_headers_log.py", "tests/unit/test_websec_headers_log.py", "tests/fixtures/webapp/websec1xx/headers_log/**"]
+++

Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/unit/test_websec_headers_log.py::test_websec_headers_log_findings_fixture[websec120_positive-WEBSEC120-True]

The WEBSEC120 positive fixture (websec120_positive) fires ZERO findings
for rule WEBSEC120 where the test's MUST-FIRE positive control expects
>=1 (AssertionError: (); assert 0 >= 1).

Both the test file and the production symbol under test
(src/frob/webapp/_websec_headers_log.py::websec_headers_log_findings, per
the file's own frob:tests directive) are inside src/frob/webapp/** --
OUT of touch-scope for this drain (other-agent-owned). Filed and handed
off whole, not fixed here.
