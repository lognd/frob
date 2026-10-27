+++
id = "01M1T07J4B86DVT7S7K3G5DPGD"
title = "--root flag + config locator line (r19, A-092)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:42Z"
aliases = ["crunk:T-0139"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/__main__.py", "src/crunk/app/app.py", "tests/unit/test_app.py", "tests/system/test_e2e_59_root_locator.py", "docs/commands/check.md", "src/crunk/app/config.py"]

[[acceptance]]
text = "given check --config proj/crunk.toml from one directory up, when it runs, then the locator line names cwd as root, and adding --root proj reproduces the in-project findings exactly"
bound = false

[[acceptance]]
text = "given a plain in-project run, when it completes, then no locator line prints"
bound = false
+++

Implement the r19 design: --root PATH exposed beside --config on every pipeline command (default cwd unchanged); every run with config set prints the locator line naming the resolved spec and root before other output; the check command doc gains both flags.
