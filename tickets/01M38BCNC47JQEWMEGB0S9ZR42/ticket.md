+++
id = "01M38BCNC47JQEWMEGB0S9ZR42"
title = "WEBSEC403 full-strength server-route cross-reference"
type = "task"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:00Z"
aliases = ["T-5508"]
labels = ["v1-cluster:B2", "area:grimble"]
scope = ["src/frob/webapp/_websec_authz_routes.py"]
+++

found while working T-5357: WEBSEC403 currently checks only that a React Router admin-path <Route> is wrapped in a guard component, a JSX-local text-regex proxy. The ticket body's full corpus item is a React router-guard AST cross-referenced against the server's own route table (built from the same WEBSEC402 admin-route detection) to confirm the client guard has a matching server-side enforcement. Implement the cross-reference.
