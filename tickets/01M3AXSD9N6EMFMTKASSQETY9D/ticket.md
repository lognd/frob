+++
id = "01M3AXSD9N6EMFMTKASSQETY9D"
title = "STORE2xx repo-fact rules"
type = "story"
category = "triage"
priority = "medium"
parent = "01M38BCP8YSPMT8SG9Y3VM7F8C"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6453"]
labels = ["milestone:0.538.0", "v1-cluster:B1", "area:grimble"]
+++

Every research row tagged `Static: config` -- a call shape paired with
one schema/config/repo fact (DDL column type, index list, persistence
config file, connection-object identity) read alongside the call site,
still no runtime data needed (DB-PARADIGM-ASSESSMENT.md's tier 2). Every
leaf is blocked by T-STORE-101-SCAFFOLD for the same detection/findings-
function substrate Story 1 uses; leaves needing a schema/config reader
document which file(s) they read in their own body rather than each
re-implementing a DDL/config scan.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
