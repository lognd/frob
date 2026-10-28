+++
id = "01M4H0RSP2HVXYS4BNCY9W8WYP"
title = "Bind each consolidated spec section to the code it specifies with frob:doc (code side) or frob:describes (doc side) so DRIFT fires when either changes; start with the rule and binding specs"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T19:03:20Z"
updated = "2026-10-28T12:57:45Z"
labels = ["docs", "no-story"]
scope = ["crates/**", "docs/**", "changelog.d/**"]

[[acceptance]]
text = "Given the consolidated specs, when the binding pass lands, then every spec section that names a rule family or a verb carries a frob:doc or frob:describes pair with the implementing symbols, and editing either side raises DRIFT until acked"
bound = false
+++

Audit: no production code binds into docs/design, so spec-vs-code drift (e.g. SYS003 meaning changed) is invisible. Depends on the shared-spec consolidation phase and ~H0RPXYR (frob:describes).

no-story: internal engineering task in crates/**; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
