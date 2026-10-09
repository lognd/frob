+++
id = "01M4FDBERB4M7E9RG2HD4J3YZ2"
title = "P4 grmb planning: verified_by arm coverage, PLAN006, derived V-model levels into kernel closure"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M4FDAD29CBF7S4EM2FKR5TXQ"
reporter = "lognd"
created = "2026-10-09T04:04:45Z"
updated = "2026-10-09T05:08:25Z"
labels = ["grimble"]
scope = ["crates/grimble-bind/**", "crates/grimble-check/**", "crates/grimble-model/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FDBDC401KMNN4C12QTA3PK"

[[acceptance]]
text = "Given checkout of grmb-planning.md 12 with evidence only for the ok path, when grimble check runs, then PLAN006 names the declined and timeout arms and nothing else"
bound = false

[[acceptance]]
text = "Given a model mixing vmodel entities and planning entities with one orphan goal leaf, when the closure runs, then exactly one finding (PLAN001) is reported for it"
bound = false

[[acceptance]]
text = "Given a test entity backed by several runner ids and a manual test entity with no runner (repro 13 in ~/projects/frob-v2-repros/logand-grimble-20261009/13-vmodel-runnable-one-or-manual), when the closure runs, then neither is SYS003 or MDL014 and the manual test is reported as manual evidence, not as missing; see ticket ~P7APFVH"
bound = false
+++

grmb-planning.md 6.2 and 6.3, row P4. verified_by ... for STEP.VARIANT arm evidence and arm anchors; PLAN006; derived V-model levels and refines links fed to the kernel closure rules with suppression so one root cause gives one finding.
