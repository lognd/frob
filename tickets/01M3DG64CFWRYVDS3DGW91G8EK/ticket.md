+++
id = "01M3DG64CFWRYVDS3DGW91G8EK"
title = "`frob ticket done-report` (no --fix) mutates the tree: its internal scoped check wrote 60 frob:tests directive lines into test files"
type = "bug"
category = "todo"
priority = "medium"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:42Z"
aliases = ["T-6543"]
labels = ["v1-cluster:C2", "triage:accepted"]
scope = ["src/frob/tickets/_done_report.py", "src/frob/check/__init__.py", "src/frob/gates/_fix_engine.py", "tests/unit/tickets/test_done_report_readonly.py", "docs/modules/tickets-lifecycle.md", "docs/design/tickets.md"]
+++

Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-409: `frob ticket done-report T-0442` with no --fix flag ran its internal scoped-check pass and silently wrote ~60 unrelated `frob:tests` directive lines into backend/tests/unit/test_*.py and tests/unit/test_*.py (the T-4710 TEST010 move shape). Nothing was staged; the agent caught it with `git status` and discarded the edits. Same family as F-398 (T-draft-4584c2f5). Deliver: (1) every verb that spawns `frob check` for measurement (done-report, close, evidence --check, land pre-checks, verify) passes an explicit read-only mode and the fix engine refuses to apply Tier-A fixes unless the top-level invocation asked for --fix; (2) a guard in the fix engine that asserts the tree hash is unchanged after a read-only check and raises loudly (naming the files) if not; (3) positive control: a fixture repo with a fixable TEST010 finding; `frob ticket done-report` leaves `git status` empty while `frob check --fix` changes the file.
