---
id: T-0155
title: 'design lint family: caching, resource bounds, rate-limiting, kill-switch rules
  over the kernel model'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0154
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- tickets.md
- design/litmus/audit_hardened.strata
- tests/system/test_cli_sys_audit.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_lint.py::TestEvaluateLint::test_evaluate_lint_aggregates_every_rule
- tests/unit/strata/test_litmus_lint.py::TestLintVulnLitmus::test_vuln_fires_every_rule
- tests/unit/strata/test_litmus_lint.py::TestLintHardenedLitmus::test_hardened_discharges_every_fired_obligation
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_lint_gap_reported
- tests/unit/strata/test_audit.py::TestHardenedLitmus::test_hardened_clean
- tests/unit/strata/test_litmus_audit_hardened.py::TestAuditHardenedGolden::test_proves_clean_in_security_and_quality
- tests/system/test_cli_sys_audit.py::TestSysAuditCli::test_clean_model_exits_zero
designated_repro_test: null
threat: null
component: null
---
Scope widened (T-0155 sweep, post-implementation): the new LINT001 rate-limit check fires on two pre-existing fixtures outside the original scope globs (`design/litmus/audit_hardened.strata`'s foreign-sourced `f_browse` flow, and `tests/system/test_cli_sys_audit.py`'s `_CLEAN_MODEL` fixture) as a direct, required consequence of wiring `evaluate_lint` into `frob sys audit`'s `evaluate_exhaustiveness` -- both received a minimal, mechanical `rate` declaration to stay green, per the ticket's own "expect cascading consequences per T-0150/T-0151 precedent" note.

Operational design linting over the kernel model, as a new rule family alongside SYS100-102. INVESTIGATE FIRST: the scenario engine (node loss, rate surge, trust downgrade -- T-0073), Bound/capacity claims, and quantity grammar (rates, sizes) -- reuse their vocabulary. Rules (each loud, waivable only with reason, drift-locked in a rule registry): LINT: public/edge boundary accepting external flows without a declared rate limit; store consumed by flows whose declared rate exceeds the store's declared service rate without a caching/TTL declaration; node participating in a surge scenario without a capacity Bound claim; node holding a risky capability (exec/net per the may declarations from T-0150) without a declared kill-switch/flag mechanism; flow fan-in exceeding declared downstream capacity. Each rule needs a written justification of WHY the kernel can express it (or an honest OutOfScope-style entry if it cannot yet -- follow the threat catalog discipline); fire/discharge litmus fixtures from parsed surface; wired into frob sys audit output beside self-conformance. Apply to design/frob.strata itself and make it green honestly (declare real rate/caching/capacity facts or waive with reasons -- expect cascading consequences per T-0150/T-0151 precedent).