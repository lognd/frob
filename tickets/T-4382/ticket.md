---
id: T-4382
title: COV003 must attribute platform-unavailable evidence, not report it as missing
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect.py
- src/frob/testing/_models.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a done ticket whose evidence node id lives in a test module that pytest
    --collect-only skips at import time via allow_module_level=True for a platform
    reason (e.g. tests/unit/test_stackdump.py's POSIX-only SIGUSR1 tests on Windows),
    when frob check runs COV003 on that platform, then the evidence is reported as
    platform-unavailable (naming the excluding platform/reason) rather than as COV003
    'does not resolve to a collected test'
  evidence: []
- text: given the same ticket/evidence on a platform where the module is NOT skipped,
    when frob check runs COV003, then normal COV003 missing-evidence enforcement is
    unchanged (this is additive, not a blanket exemption)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured on Windows CI run 34371162715 (win4.log): frob check on Windows produced 58 errors including gate:COV=56, dominated by COV003 (112 raw hits per the run's own self-gate summary). Root cause traced to tests/unit/test_stackdump.py (and likely other POSIX-only modules) using pytest.skip(..., allow_module_level=True) guarded by a sys.platform check -- this makes pytest --collect-only never emit those node ids AT ALL on Windows, so any frob:tests/evidence pointing at them fails _evidence_valid_for_ticket and COV003 reports 'does not resolve to a collected test', indistinguishable from a genuinely missing/broken test. Searched tickets/*/ticket.md for an existing platform-conditional-evidence ticket first (none found). Precedent: CollectedTests.missing_natives already carries an analogous distinct-cause field (T-0333) that lets COV003 name the real remedy instead of blaming the evidence id -- this ticket asks for the same shape for platform-skipped modules: parse pytest --collect-only -rs skip lines for allow_module_level module skips, record (file, reason) on CollectedTests, and have COV003's evidence check attribute matches to a distinct non-error outcome naming the excluding platform, instead of the current ERROR. Implement with a test that plants a test module skipped via allow_module_level on the current platform and asserts COV003 does NOT fire ERROR for evidence pointing at it.