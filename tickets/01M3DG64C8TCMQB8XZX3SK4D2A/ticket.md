+++
id = "01M3DG64C8TCMQB8XZX3SK4D2A"
title = "web rule modules print progress to stdout from library calls; route through the module logger"
type = "bug"
category = "triage"
priority = "medium"
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-09-26T00:00:00Z"
aliases = ["T-6536"]
labels = ["milestone:0.534.0", "v1-cluster:B2", "area:grimble"]
scope = ["src/frob/webapp/_websec_sinks.py", "src/frob/gates/_a11y_gate.py", "src/frob/gates/_taint_gate.py", "tests/unit/test_webapp_no_stdout.py"]
+++

Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-395: calling `taint_gate(Path('frontend'))` and `a11y_gate` from Python prints ~226 lines like 'websec_sinks: 32 finding(s) under ...' and 'a11y_findings: 0 violation(s) in X' to stdout, plus a WARNING that `_a11y_substrate` matches the hook prefix but exposes no a11y_findings. Deliver: every such line moves to the module logger at DEBUG/INFO (RENDER001 already forbids bare stdout writes; extend its coverage to these modules), the substrate-prefix warning is silenced for modules that intentionally expose no hook, and a test captures stdout across a gate call and asserts it is empty.
