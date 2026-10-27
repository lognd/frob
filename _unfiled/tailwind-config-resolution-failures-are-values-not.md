+++
id = "01M1T07J3E3RKFZ29QJTHX1S73"
title = "tailwind config resolution failures are values, not tracebacks (A-050.1)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-27T00:53:39Z"
aliases = ["crunk:T-0110"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/ingest/walk.py", "src/crunk/ingest/tailwind.py", "tests/unit/test_ingest.py"]

[[acceptance]]
text = "given a tailwind config path whose resolution fails (bad symlink, permission, missing), when check runs, then a ParseDiagnostic names the path and reason and the run continues; no traceback"
bound = false
+++

Field crash: a mis-based node_modules symlink made check throw a raw path-resolution traceback. Every OS-level failure reading/resolving the configured tailwind config becomes a ParseDiagnostic (the walk survives, as with any unreadable file).
