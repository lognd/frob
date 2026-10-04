+++
id = "01M35RZY85GEZN4JH37RJCDRVW"
title = "extending-guide anchor T-4118 fragment stale: frob.tickets._models.py cites a slug the guide no longer has"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5381"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/tickets/_models.py", "docs/guides/extending/failure-injection-acceptance-criteria.md"]
+++

CI run 35819358270 (all 3 platforms); re-verified failing on dev tip 39b89ed091: tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1 fails -- src/frob/tickets/_models.py's DOC002 anchor cites fragment '#failure-injection-acceptance-criteria-name-every-field-t-4118' but docs/guides/extending/failure-injection-acceptance-criteria.md's current H1 slug is 'failure-injection-acceptance-criteria-name-every-field' (no trailing -t-4118). Either the guide's heading was renamed/retitled and the anchor needs updating, or the anchor's trailing ticket-id suffix is now stale. Not covered by any open ticket found.
