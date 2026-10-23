+++
id = "01M1QDTV1DCN8AAT89YVFGC3T4"
title = "Register ORG005 in frob gate WIRE _KNOWN_GATE_RULES"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0045"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/frob/gates/_waive.py"]
+++

found while working T-0035: rules/_org.py::org005 emits rule=ORG005, which src/frob/gates/_waive.py's _KNOWN_GATE_RULES does not list yet (WIRE001). That file is outside T-0035's declared scope (crunk source), so filing separately rather than expanding scope.

## Drop reason
- 2026-09-05: duplicate of standing upstream marker T-0023 (register crunk domain rule ids in frob's _KNOWN_GATE_RULES); consolidated there
