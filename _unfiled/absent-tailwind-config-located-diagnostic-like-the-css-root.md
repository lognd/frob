+++
id = "01M1T07J42BYAD1FDNJHY06C0F"
title = "Absent tailwind config: located diagnostic like the css root (A-074)"
type = "task"
flavour = "ux"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:41Z"
aliases = ["crunk:T-0130"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/ingest/walk.py", "tests/unit/test_ingest.py", "docs/design/subsystems/ingest.md"]

[[acceptance]]
text = "given a spec naming a tailwind config that does not exist, when ingested, then the diagnostic reads tailwind config <path> does not exist with the theme falling back and no bare errno text"
bound = false
+++

The engine-branch run prints a bare errno line for a missing tailwind config while the absent css root prints the r15 located-diagnostic shape. Consistency fix: when the configured tailwind config path simply does not exist, the diagnostic message becomes the documented shape naming the resolved path; other OS failures keep the OS reason.
