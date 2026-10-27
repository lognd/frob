+++
id = "01M1QDTV38SJ2596PJFEEW1NYG"
title = "R11-A: self-derived tw_theme + alpha-modifier stripping (A-045, A-047)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:39Z"
aliases = ["crunk:T-0104"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/tokens/render.py", "src/crunk/tokens/__init__.py", "src/crunk/app/app.py", "src/crunk/query/engine.py", "tests/unit/test_tokens.py", "tests/unit/test_query.py", "tests/unit/test_app.py", "tests/system/test_e2e_45_selfmap.py"]

[[acceptance]]
text = "given a tailwind config that only imports the generated mapping, when explain and check --report run against a TSX using bg-<token>/70, then explain lists the site and utility and unused_tokens excludes every utility-consumed token (E2E-45)"
bound = false
+++

Per r11 tokens.md (theme_mapping public), shell.md (r11 wiring overlay), query.md (alpha stripping): tokens.theme_mapping(spec) returns the flat utility-key->value mapping exactly as render_tailwind emits (namespace_keys/alpha_channels aware); the shell overlays it onto styles.tw_theme via model_copy whenever the tokens file is configured (heuristic parse stays as merge base); query.utility_token_map strips /<digits> alpha modifiers from utility names before value-part matching. Regression fixture MUST use the require()-style config with zero literal entries -- the field shape that exposed the gap.
