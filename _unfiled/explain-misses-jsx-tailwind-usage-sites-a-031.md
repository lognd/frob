+++
id = "01M1QDTV2PJJ72HPR2R7P2HSQ2"
title = "explain misses JSX/Tailwind usage sites (A-031)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:37Z"
aliases = ["crunk:T-0086"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/query/engine.py", "src/crunk/query/models.py", "src/crunk/app/app.py", "tests/unit/test_query.py", "tests/unit/test_app.py", "tests/system/test_e2e_32_explain.py", "tests/system/test_e2e_34_explain_jsx.py"]

[[acceptance]]
text = "given a token referenced ONLY via a Tailwind utility in TSX (e.g. bg-bg-primary with an empty color prefix), when crunk explain runs, then the TSX site and the utility both list, and query unused does not list the token (E2E-34)"
bound = false
+++

Field bug from the re-trial: explain reported 'no sites reference it' and 'utilities: (none)' for the app's most-used colors -- would have caused real deletions. Per r8 query.md: sites MUST include each LocatedUtility whose mapped token equals the explained name, as (sheet path, line), from the same ingest pass check uses. Diagnose why the T-0082 wiring produced empty utilities on the real shell (their utilities look like bg-bg-primary with color prefix '' -- suspect the utility value-part -> theme-key -> token mapping direction or the empty-prefix name shapes) and pin the exact field shape in the regression fixture: the tokens prefix table with color = '', palette key bg-primary, tailwind theme entry 'bg-primary': 'var(--bg-primary)', TSX className 'bg-bg-primary'.
