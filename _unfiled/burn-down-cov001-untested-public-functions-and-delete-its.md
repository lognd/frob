+++
id = "01M6H40PZZE3V5ZA9DD3T6JNG5"
title = "Burn down COV001 (untested public functions) and delete its off table"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-03T16:31:29Z"
updated = "2026-11-03T20:30:01Z"
labels = ["no-story"]
scope = ["crates/**", ".github/**", "scripts/claude-hooks", "frob.toml", "packaging/pypi/test_render.py/**", "tests/claude_hooks/**", "tests/scripts/**", "packaging/pypi/test_render.py", "tests/scripts/test_shell_scripts.py"]

[[acceptance]]
text = "frob.toml has no rules.COV001 table"
bound = true

[[acceptance]]
text = "frob check reports zero COV001 findings"
bound = true
+++

307 findings with COV001 on (errors + unresolved). Add real tests or frob:tests bindings; delete [rules.COV001] off table in frob.toml at zero.
