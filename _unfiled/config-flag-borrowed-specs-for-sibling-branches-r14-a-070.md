+++
id = "01M1T07J3ZX9JBNHFHJVTJ5J7X"
title = "--config flag: borrowed specs for sibling branches (r14, A-070)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["crunk:T-0127"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/app/config.py", "src/crunk/app/app.py", "src/crunk/__main__.py", "tests/unit/test_app.py", "tests/system/test_e2e_52_config.py", "docs/commands/check.md"]

[[acceptance]]
text = "given a tree with no crunk.toml, when check --config other/crunk.toml runs, then judgments run against the borrowed spec and without the flag the missing-spec failure names crunk.toml"
bound = false

[[acceptance]]
text = "given a bogus --config path, when any pipeline command runs, then it exits 2 naming that path"
bound = false
+++

Implement the r14 A-070 design: global explicit --config PATH loading the spec via load_spec_file(path, root) while root stays cwd; no upward discovery; missing path is the standard SpecFailure naming the given path; cache correctness follows from the byte-keyed cache.
