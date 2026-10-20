+++
id = "01M15D1X8VJBCPY6V0XFES6YPZ"
title = "frob:debt does not actually suppress the gate finding it documents suppressing"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-08-29T00:00:00Z"
updated = "2026-10-04T21:07:35Z"
aliases = ["T-3355"]
labels = ["milestone:0.541.0", "v1-cluster:F1"]
scope = ["src/frob/gates/_waive.py", "src/frob/gates/_debt_deprecated.py"]
+++

docs/guides/extending/comment-dsl-directives.md states 'frob:debt suppresses a GATE FINDING (the symptom)' -- but _apply_waivers (src/frob/gates/_waive.py) only reads EdgeKind.WAIVE via _waive_edges/_waivers_by_rule; EdgeKind.DEBT edges are never consulted there, only by debt_gate's own DEBT001-003 self-checks. Measured directly: converting a frob:waive to frob:debt (T-3295) makes the underlying gate finding (AFFECT001/COV001) reappear LIVE in frob check output rather than staying suppressed as the doc promises. Either the doc is aspirational and wrong (frob:debt was only ever meant to track, never suppress -- fix the doc), or _apply_waivers should also match DEBT edges the same way it matches WAIVE edges (fix the code). Found while converting T-3295's misclassified waivers -- did not fix here, outside that ticket's declared scope and this is a real design decision, not a quick patch.
