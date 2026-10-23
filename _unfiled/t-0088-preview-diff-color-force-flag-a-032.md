+++
id = "01M1QDTV2RJ8GR3JVDGBDHXW4D"
title = "preview/diff --color force flag (A-032)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0088"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/__main__.py", "src/crunk/app/config.py", "src/crunk/app/app.py", "tests/unit/test_main.py", "tests/unit/test_app.py", "tests/system/test_e2e_35_color_flag.py", "docs/commands/preview.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV2PJJ72HPR2R7P2HSQ2"

[[acceptance]]
text = "given a piped stdout, when crunk preview --color runs, then ANSI escapes appear; without the flag the piped run stays plain; NO_COLOR beats the flag (E2E-35)"
bound = false
+++

Per r8 report.md/02: --color on preview and diff forces use_color=True at the call site (renderers unchanged); NO_COLOR still wins, documented in docs/commands/preview.md. Also verify a real-TTY run emits swatch escapes at all (the field report suspected none; the unit goldens say color-on works -- add an e2e asserting escapes under --color to settle it).
