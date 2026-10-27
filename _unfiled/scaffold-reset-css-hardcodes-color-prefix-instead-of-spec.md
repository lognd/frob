+++
id = "01M1QDTV19ZQKEQX7WHEA4QM6B"
title = "scaffold reset.css hardcodes --color- prefix instead of spec.naming"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:32Z"
aliases = ["crunk:T-0041"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/scaffold/write.py", "tests/unit/test_scaffold.py"]
+++

found while working T-0032: _reset_css() in scaffold/write.py builds var(--color-{fg})/var(--color-{bg}) as raw f-strings instead of using crunk.spec.naming.color_token(spec.tokens, name). With a non-default (e.g. empty) tokens-prefix-table color prefix, the scaffolded starter reset.css references undefined tokens and check fails immediately after init.
