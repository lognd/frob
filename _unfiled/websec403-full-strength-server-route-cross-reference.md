+++
id = "01M38BCNC47JQEWMEGB0S9ZR42"
title = "WEBSEC403 full-strength server-route cross-reference"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-28T12:55:40Z"
aliases = ["T-5508"]
labels = ["v1-cluster:B2", "area:grimble", "triage:accepted", "milestone:0.538.0", "no-story"]
scope = ["src/frob/webapp/_websec_authz_routes.py"]
+++

found while working T-5357: WEBSEC403 currently checks only that a React Router admin-path <Route> is wrapped in a guard component, a JSX-local text-regex proxy. The ticket body's full corpus item is a React router-guard AST cross-referenced against the server's own route table (built from the same WEBSEC402 admin-route detection) to confirm the client guard has a matching server-side enforcement. Implement the cross-reference.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
