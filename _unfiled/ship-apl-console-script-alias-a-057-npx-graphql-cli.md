+++
id = "01M1T07J3MVCCZM2X6AD0JA3N4"
title = "Ship apl console-script alias (A-057 npx GraphQL-CLI collision)"
type = "task"
flavour = "ux"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:40Z"
aliases = ["crunk:T-0116"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["pyproject.toml", "docs/design/subsystems/shell.md"]

[[acceptance]]
text = "given the installed tool, when apl check runs, then it is the same entrypoint as crunk check"
bound = true
+++

The adopting project agent ran npx crunk check and got the deprecated GraphQL CLI from npm. A second console script apl pointing at the same entry gives an unambiguous short name; shell.md documents the alias.
