+++
id = "01M1J91D0Y0WT1X93G2MJFTXEE"
title = "post-land sweep regression from an unattributed source (sweep spawned by T-0016): 4 new (rule, file) identit(ies), 10 finding(s) (TEST006, WAIVE006)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-03T00:00:00Z"
updated = "2026-09-03T00:00:02Z"
aliases = ["crunk:T-0030"]
labels = ["component:crunk", "source:crunk"]
scope = [".frob/coverage-stamp", "src/crunk/rules/engine.py", "src/crunk/values/color.py", "src/crunk/values/length.py", "docs/design/subsystems/rules.md", "docs/design/subsystems/values.md", "frob-coverage.lock.json", "coverage.xml"]
+++

The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-0016) at commit 49848efe7ecd8430aacbb92b9a810baf312360ea found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (4), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 10 actual finding(s) across those 4 identit(ies).

New (rule, file) identit(ies) filed here:

- TEST006  .frob/coverage-stamp
- WAIVE006  src/crunk/rules/engine.py
- WAIVE006  src/crunk/values/color.py
- WAIVE006  src/crunk/values/length.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- TEST006  .frob/coverage-stamp  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WAIVE006  src/crunk/rules/engine.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WAIVE006  src/crunk/values/color.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WAIVE006  src/crunk/values/length.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.
