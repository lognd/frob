---
id: T-1046
title: 'fix test_clean_model_exits_zero: add missing timeout attr, REL200 correctly
  flags flow'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_sys_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_clean_model_exits_zero
designated_repro_test: null
threat: null
component: null
---
test_clean_model_exits_zero's _CLEAN_MODEL fixture declares flow f1
(evil -> api) with a rate attr but no timeout attr and no async/local
exemption -- REL200 (missing-timeout obligation, long-standing since
T-0640, unchanged in the last 24h per git log against
src/frob/strata/_reliability.py) correctly flags this as a real gap.

Verified: check_reliability_timeouts logic and the deny-by-default
policy for REL200 are unmodified; parse_module/elaborate on the exact
fixture text confirms attrs=() on f1 (no silent parser drop). Verified
"uv run frob sys audit" on the real repo model is clean (PROVED, exit
0) -- the regression is confined to this test's fixture, not a real
repo violation.

Root cause is most likely that a recent strata-core grammar/parser
change (T-0700's parse.rs rewrite, or a related native fix) started
correctly elaborating this exact rate-quantity flow shape for the
first time, surfacing a pre-existing, always-true gap that a
parser/elaboration bug previously masked -- the fixture itself was
never actually REL200-clean.

Honest fix per the audit instructions: fix the violation (add attr
timeout to the fixture) rather than weaken or stamp around REL200. No
production code touched.