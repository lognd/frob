+++
id = "01M1QDTV2XV4EZPT4BFPRHV9AB"
title = "alpha_channels emission + TW003 silent-alpha lint (A-035)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:38Z"
aliases = ["crunk:T-0093"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/tokens/render.py", "src/crunk/rules/_tailwind.py", "src/crunk/rules/engine.py", "src/crunk/spec/models.py", "tests/unit/test_tokens.py", "tests/unit/test_rules_tailwind.py", "tests/system/test_e2e_37_alpha_channels.py", "docs/commands/tokens.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV2VWVTBD67DJ88JSHZE"

[[acceptance]]
text = "given alpha_channels = true, when tokens runs, then tokens.css carries -rgb triplets and the theme maps colors in the alpha-capable form; a bg-x/50 utility against non-alpha emission yields TW003 and against alpha emission does not (E2E-37)"
bound = false
+++

Per r9 tokens.md (alpha_channels bullet) and rules.md (TW003): render_css emits --<color token>-rgb R G B triplets per palette entry when the knob is on (export set/drift automatically covered); render_tailwind maps colors as rgb(var(<token>-rgb) / <alpha-value>); catalog gains (TW,3,warn); tw003 per rules.md (utility name containing / with numeric suffix, value-part maps to a theme color entry lacking the <alpha-value> placeholder). The knob field landed with T-0091.
