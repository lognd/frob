+++
id = "01M1WJMD3TQM3XY04FW9BAGVE9"
title = "strata: declare client-persisted browser storage as a capability with cleared_on triggers, and require a code path per trigger"
type = "task"
category = "todo"
priority = "low"
parent = "01M1WJMD1X14Z9P76XPX0QQ0NM"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-4218"]
labels = ["v1-cluster:B3d", "triage:accepted"]
scope = ["src/frob/strata"]
+++

Consolidates T-4157/H4-7 (localStorage used with SPEC-023 saying 'no storage' -- undeclared privacy-surface import, would fail SYS100 if declared as a capability e.g. browser.local_storage) with F-362/M4-6 (T-4166 -- a return-path stash's lifecycle has write/consume/invalidate-on-logout events and only two are implemented; declare browser-persisted state with cleared_on='logout,consume' and require a code path for each declared trigger). Not fixture-testable in frob's own tree: no browser storage surface exists here.
