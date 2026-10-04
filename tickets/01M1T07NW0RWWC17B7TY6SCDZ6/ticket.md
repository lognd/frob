+++
id = "01M1T07NW0RWWC17B7TY6SCDZ6"
title = "route/guard inventory: CSRF, confirm-gate and pagination axes"
type = "security"
category = "todo"
priority = "low"
parent = "01M1QDTYTFZHQYMDHNFBSGQXJJ"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3968"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/vet/_capability.py"]

[[acceptance]]
text = "given a design note choosing target framework(s) and how routes are discovered, when this ticket's design step completes, then the note is attached before axis implementation begins"
bound = false

[[acceptance]]
text = "given the design is accepted, when implemented, then a mutating route missing a CSRF guard, a destructive route missing a confirm gate, or a list route with no pagination bound is each independently reportable"
bound = false
+++

T-3919 item 7 (guard-registry completeness) plus T-3942 item 10 (F-184, extending the same inventory to a confirm-gate axis and a pagination axis), combined into one ticket because both ask for the SAME underlying capability: a machine-checkable route inventory over a web framework's routes. VERIFIED: git grep for "route inventory", "guard registry", "SIT-011", "SIT011" across src/frob found NOTHING -- this capability does not exist in frob at all today; it is entirely a consumer-repo construct (their own SIT-011 checker) that frob has no equivalent of. This is a genuinely new capability, not a duplicate.

FINDING THIS WOULD HAVE CAUGHT (T-3919 item 7): their own machine-checkable route inventory has an auth-guard axis but omits CSRF -- extend "has an auth guard" to "every mutating route has an auth guard AND a CSRF guard, or is on a declared exemption list."

FINDING THIS WOULD HAVE CAUGHT (T-3942 item 10 / F-184): the same inventory needs a third and fourth axis -- a confirm-gate axis (does a destructive route require an explicit confirm step) and a pagination axis (does a list-returning route bound its result set) -- both readable mechanically from the route's pydantic request/response model and its function signature, without new taint analysis.

SCOPE NOTE: this is a NEW capability (frob has no route-inventory concept today), so the leaf work is: (1) design the route-inventory data model (what counts as a route, how a framework's routing table is discovered per-language/per-framework), (2) the auth+CSRF axis, (3) the confirm-gate axis, (4) the pagination axis. Recommend splitting (1) out as its own prerequisite ticket once a framework target is chosen, since "which frameworks" materially changes the design.
