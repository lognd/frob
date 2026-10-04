+++
id = "01M336K75NMT3A5A562PMFWHYX"
title = "Gate rule-id registration and severity wiring for WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5301"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/gates/_waive.py", "frob.toml", "docs/modules/gates.md", "tests/gates_suite/test_coverage.py", "docs/design/registry/check-coverage.yaml"]
+++

Add all WEBSEC/COMPLY/A11Y/SEO/WEBPERF/SQL rule-id ranges to _KNOWN_GATE_RULES as a reserved block (placeholder comments naming the future ticket, same shape as PERF015-018's T-5136 reservation) so frob:waive on an unshipped rule id fails loud, not silently. Add a [gates.severity] block: WEBSEC/COMPLY/A11Y default error; SEO/WEBPERF default warn until a repo opts to promote (PERF015-018 precedent). LAUNCH severity is handled separately by WEBSUB-4 (new advisory tier), not this leaf. Positive-control: frob:waive WEBSEC101 reason=... round-trips through known-rule-id checks without raising UnknownRuleId once this leaf lands. Doc: docs/modules/gates.md's rule table (skeleton rows).
