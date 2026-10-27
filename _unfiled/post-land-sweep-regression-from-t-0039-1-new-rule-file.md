+++
id = "01M1QDTV1ERR372T9KFTACKNTY"
title = "post-land sweep regression from T-0039: 1 new (rule, file) identit(ies), 1 finding(s) (OPAQUE001)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:32Z"
aliases = ["crunk:T-0046"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/__main__.py"]
+++

The deferred post-land unscoped sweep (T-1684) for T-0039 at commit 652dc2977d1352f53b2727d2a451a07739613380 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- OPAQUE001  src/crunk/__main__.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- OPAQUE001  src/crunk/__main__.py  -> attributed to T-0039 (commit 652dc2977d13, already closed/dropped -- filed below) via src/crunk/__main__.py::_build_parser
- TEST006  tests/integration/test_int_10_query.py  -> attributed to T-0039 (commit 652dc2977d13, already closed/dropped -- filed below) via tests/integration/test_int_10_query.py::_query

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
