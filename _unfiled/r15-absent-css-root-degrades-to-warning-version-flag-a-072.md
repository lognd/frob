+++
id = "01M1T07J40ZJBZ9BJY3QCENHNA"
title = "r15: absent css root degrades to warning; --version flag (A-072)"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:41Z"
aliases = ["crunk:T-0128"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["docs/design/02-specification.md", "docs/design/subsystems/ingest.md", "docs/design/subsystems/shell.md", "docs/design/01-customer-requirements.md"]

[[acceptance]]
text = "given the four docs, when read, then the absent-css-root degradation, the path-named errors, the version flag, and CT/E2E ids are stated"
bound = true
+++

The engine branch borrowing a spec has no css root at all, and the walk hard-fails with an unlocated OS-failure message, blocking the jsx and tailwind judgments that WOULD apply. r15: an ABSENT css root becomes a ParseDiagnostic-style warning naming the resolved path, the walk proceeds with zero sheets so jsx/tailwind rules still run (never a silent skip; other OS failures still error, now naming the path). Also a real --version flag; the short -v stays verbose.
