+++
id = "01M1QDTV1AX55ZV5341XDEZ8AT"
title = "unify CONTRAST_AA_FLOOR into crunk.spec.models once T-0032 lease clears"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0042"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/spec/models.py", "src/crunk/rules/_contrast.py", "src/crunk/report/terminal.py", "src/crunk/report/json_out.py", "docs/design/subsystems/report.md", "src/crunk/app/app.py", "src/crunk/spec/naming.py", "src/crunk/tokens/render.py", "tests/unit/test_spec.py", "tests/unit/test_tokens.py", "src/crunk/__main__.py", "docs/design/subsystems/rules.md", "docs/design/subsystems/spec.md", "docs/design/subsystems/tokens.md", "docs/design/subsystems/shell.md", "docs/index.md"]

[[acceptance]]
text = "the 4.5 AA floor has exactly one definition, imported by rules/_contrast.py and report/terminal.py alike"
bound = false
+++

T-0033 wanted a single home for the 4.5 AA contrast floor (crunk.spec.models.CONTRAST_AA_FLOOR, mirroring RULE_IDS/DEFAULT_SEVERITY) but src/crunk/spec/** was under an active scope lease held by T-0032 at implementation time. report.terminal.CONTRAST_AA_FLOOR and rules/_contrast.py::_AA_FLOOR are therefore two separate copies of the same constant -- unify them once the lease clears.
