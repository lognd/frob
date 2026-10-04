+++
id = "01M35RZYAEACPHW0NRKYR6CVYZ"
title = "Fix a11y_findings signature to match T-5323 per-file gate contract"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5454"]
scope = ["src/frob/webapp/_a11y_statement.py", "tests/unit/test_webapp_a11y_statement.py"]
+++

T-5323's a11y_gate() calls every discovered hook as a11y_findings(ctx: A11yFileContext, frameworks) once per parsed file; src/frob/webapp/_a11y_statement.py still implements a11y_findings(root: Path, frameworks), so frob.gates._a11y_gate.a11y_gate() crashes with TypeError on any repo with a detected framework. Rework to the per-file contract (memoized repo-level statement detection), keep A11Y107-114 semantics and fixtures, add an end-to-end test exercising a11y_gate() over a throwaway repo.
