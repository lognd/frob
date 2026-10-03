+++
id = "01M405B09EW2M0NDNTXKHXV2X7"
title = "grimble SYS001, SYS002, SYS004: decide applicability from facts on a repository with no model entity"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:56:06Z"
updated = "2026-10-03T09:21:11Z"
idempotency_key = "m2-sys-empty-model"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/grimble-bind/**", "crates/grimble-check/**"]

[[acceptance]]
text = "Given a repository with no model entity, when grimble check runs, then SYS001, SYS002 and SYS004 are NotApplicable with reasons and frob prints no zero-subject warning"
bound = true
+++

Follow-up of ~S3AFCP4, which added fact predicates (declare_not_applicable, before evaluation) for SYS003 and SYS008-011. On a repository with no model entity, SYS001, SYS002 and SYS004 still report zero subjects and frob warns. Give each a fact predicate next to its rule, in the same mechanism, with (a) a NotApplicable test, (b) an examines-subjects test, (c) the wiring-bug test pattern from crates/grimble-check/tests/binding.rs.
