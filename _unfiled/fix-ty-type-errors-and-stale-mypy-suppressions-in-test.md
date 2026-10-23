+++
id = "01M1J91D0X4887MDVK762PR90V"
title = "fix ty type errors and stale mypy suppressions in test_report.py/test_spec.py"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-03T00:00:00Z"
updated = "2026-09-03T00:00:02Z"
aliases = ["crunk:T-0029"]
labels = ["component:crunk", "source:crunk"]
scope = ["tests/unit/test_report.py", "tests/unit/test_spec.py"]
+++

found while working T-0016 (docs pass): frob check reports pre-existing errors unrelated to docs -- [ty] tests/unit/test_report.py:57:9 invalid-argument-type (all platforms), and SUPPRESS001 at tests/unit/test_spec.py:434,443 (mypy suppression present but ty reports the ignore as unused). Both are out of T-0016's docs-only scope; present on a clean checkout before any T-0016 change.

## Drop reason
- 2026-09-03: unreproducible on main: ty check passes clean; the test_spec.py suppressions are deliberate frozen-mutation test scaffolding. The T-0016 agent measured under a PYTHONPATH-augmented env (FLAGCOV workaround) which produced phantom findings
