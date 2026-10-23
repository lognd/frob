+++
id = "01M1QDTV1ZC490G7YY856GTCNB"
title = "R6-D: tailwind theme generation from crunk.toml (CR-19)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0063"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/tokens/**", "src/crunk/app/app.py", "src/crunk/app/config.py", "src/crunk/__main__.py", "tests/unit/test_tokens.py", "tests/unit/test_app.py", "tests/unit/test_main.py", "tests/system/test_e2e_27_theme.py", "docs/commands/tokens.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV1X39GRJS23113J5FPH"

[[acceptance]]
text = "given [tailwind].tokens_file configured, when bare crunk tokens runs, then the theme mapping file is written deterministically, a palette edit changes it, hand-editing it raises TOKENS001 naming the file, and tokens --format tailwind previews without writing (E2E-27)"
bound = false
+++

Per r6 tokens.md (Tailwind theme rendering section, UT-TOK-07) and shell.md r6 wiring: render_tailwind(spec) deterministic JSON (colors/spacing/fontSize/borderRadius/zIndex/fontFamily via spec.naming); write_tokens/check_tokens extended to the configured tokens_file with TOKENS001 messages naming WHICH file; tokens --format gains the tailwind choice under the r5 preview/write contract; docs/commands/tokens.md updated.
