+++
id = "01M1WJMD3R786QZVTHZ0MVPEG2"
title = "strata: declare page-wide/global capabilities distinctly from component-local ones, with a required scoping predicate"
type = "task"
category = "triage"
priority = "medium"
parent = "01M1WJMD1X14Z9P76XPX0QQ0NM"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4216"]
labels = ["milestone:1.1.0", "v1-cluster:B3d"]
scope = ["src/frob/strata"]
+++

Consumer F-357/H4-4 (T-4157): a component installing a window-level keydown listener is a page-wide capability, not a component-local one, and no gate models the distinction. Add a global-scope capability kind (e.g. dom.global_key_capture) whose ceiling requires a declared focus-scoping predicate; a node that captures globally without one fails SYS100. Not fixture-testable in frob's own tree: no DOM/global-listener surface exists here.
