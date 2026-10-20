+++
id = "01M30M6G4D0VP6S7RYXDZYMG44"
title = "Tier-A fix for redundant production-side frob:tests declarations (T-4710 follow-up)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5261"]
scope = ["src/frob/gates/_fix_engine_text.py", "src/frob/gates/_waive.py", "src/frob/gates/_fix_engine.py", "tests/test_gates_fix_engine.py", "tests/gates_suite/test_fix_engine.py", "docs/modules/gates.md", "src/frob/gates/__init__.py"]
+++

found while working T-4710: frob.graph._redundant_test_declarations (src/frob/graph/__init__.py) now lints a frob:tests directive still declared on the production symbol as redundant (delete when a test-side declaration already exists, move-with-refusal when it does not, per T-4710's move-semantics amendment). T-4710's own scope is src/frob/graph/* only, so the Tier-A auto-fix handler (frob.gates._fix_engine_text, dispatched via TIER_A_HANDLERS) was left unbuilt; this ticket is that handler plus its _KNOWN_GATE_RULES registration and frob.toml severity.
