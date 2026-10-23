+++
id = "01M1QDTV14WYX41P0NEG5H1VX2"
title = "named typography stacks (CR-10, A-002)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0036"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/spec/load.py", "src/crunk/rules/_typography.py", "src/crunk/tokens/render.py", "tests/unit/test_spec.py", "tests/unit/test_rules_typography.py", "tests/unit/test_tokens.py", "tests/system/test_e2e_11_stacks.py", "docs/design/subsystems/spec.md", "docs/design/subsystems/rules.md", "docs/design/subsystems/tokens.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV10V68Y2CNVD2A8NT1Q"

[[links]]
kind = "blocked-by"
target = "01M1QDTV130JWWM36ATEDEAA4M"

[[acceptance]]
text = "given declared body/display stacks, when check runs on files using each, then TYPE002 passes both and fails an undeclared leading font naming the stacks; tokens exports --font-family-<stack> (E2E-11)"
bound = false
+++

Per r4: TypographyConfig.stacks dict[str, list[str]] default {}, members must be in families (case-insensitive), non-empty; TYPE002 effective-stacks semantics (prefix of ANY declared stack, families fallback unchanged); tokens exports --font-family-<stack> after base via spec.naming. UT-SPEC-07 (stacks half), UT-RUL-STACKS, UT-TOK-05 (stack part), E2E-11.
