+++
id = "01M1QDTV23JP68WEKTT38XHP5P"
title = "post-land sweep regression from T-0062: 1 new (rule, file) identit(ies), 1 finding(s) (OPAQUE001)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:35Z"
aliases = ["crunk:T-0067"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/rules/_tailwind.py", "tests/unit/test_rules_tailwind.py"]
+++

The deferred post-land unscoped sweep (T-1684) for T-0062 at commit a1d598c22d57df2226cebeceb8d90955cb4521ae found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- OPAQUE001  src/crunk/rules/_tailwind.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- OPAQUE001  src/crunk/rules/_tailwind.py  -> attributed to T-0062 (commit a1d598c22d57, already closed/dropped -- filed below) via src/crunk/rules/_tailwind.py::_ARBITRARY_RE
- TEST006  tests/system/test_e2e_29_utility_first.py  -> attributed to T-0062 (commit a1d598c22d57, already closed/dropped -- filed below) via tests/system/test_e2e_29_utility_first.py::_TOML

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
