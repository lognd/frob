+++
id = "01M1J91D0Q7JR6SR9WSYVWR6MP"
title = "register TOKENS001 in frob's _KNOWN_GATE_RULES"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-03T00:00:00Z"
updated = "2026-09-03T00:00:01Z"
aliases = ["crunk:T-0023"]
labels = ["v1-cluster:C3", "component:crunk", "source:crunk"]
scope = ["src/crunk/app/app.py"]
+++

T-0012's shell wiring constructs a TOKENS001 Violation directly in App._merge_tokens_violation (per shell.md's documented wiring decision: TOKENS001 is not produced by a rules/_*.py module like the other rule ids, it is merged by the shell from tokens.check_tokens's drift status). frob's gate:WIRE flags this construction site because TOKENS001 is not present in frob's own _KNOWN_GATE_RULES registry (src/frob/gates/_waive.py, outside this repo). Register TOKENS001 there (or add whatever registration mechanism frob exposes for gate rule ids constructed outside rules/), then remove the frob:waive WIRE001 this ticket leaves on that call site.
