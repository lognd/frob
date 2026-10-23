+++
id = "01M1QDTV2WBMMJ45GNCJWWGE53"
title = ".ts class-string constants join the scanned surface (A-036)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0092"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/ingest/jsx.py", "src/crunk/ingest/walk.py", "src/crunk/scaffold/presets.py", "tests/unit/test_ingest.py", "tests/unit/test_scaffold.py", "tests/system/test_e2e_38_ts_constants.py"]

[[acceptance]]
text = "given a .ts file exporting a class-list string constant (the audit's a11y.ts shape), when it matches the jsx globs, then its utilities reach check/explain/unused; a .ts with ordinary strings contributes nothing (E2E-38)"
bound = false
+++

Per r9 ingest.md (.ts class-string constants) and 02 (.ts scanning): matched .ts files scan STRING LITERALS that look like utility class lists (>=2 whitespace-separated utility-shaped tokens, or one arbitrary-value utility) into LocatedUtility entries; no style-prop extraction for .ts. Walk routes .ts matches through the new path; scaffold comments recommend declaring both globs. The audit case: shared a11y class constants were the one file the scanner did not read, letting a contrast regression past the check written to prevent it -- make that the regression fixture.
