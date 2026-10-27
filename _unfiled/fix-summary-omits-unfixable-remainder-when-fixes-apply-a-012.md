+++
id = "01M1QDTV1T2MK04AN9QTQGE8XW"
title = "fix summary omits unfixable remainder when fixes apply (A-012 residual)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:34Z"
aliases = ["crunk:T-0058"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/app/app.py", "tests/unit/test_app.py", "tests/system/test_e2e_20_21_ux.py"]

[[acceptance]]
text = "given one fixable and one unfixable error, when fix --dry-run runs, then the output mentions the unfixable count and exits 1"
bound = false
+++

Third trial: 'would apply 1 fix(es), 0 dropped' + exit 1 with an unfixable COLOR001 present but unmentioned. Extend the T-0052 message logic: after the per-file lines, when unwaived error-severity violations remain unfixed, print the same remainder line the no-plans branch uses.
