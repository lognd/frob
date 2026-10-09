+++
id = "01M4FF3S2QCSHSR4W6JX85A7ZD"
title = "grimble migrate: convert v1 .strata models to .grmb (code to owns, interface to surface, may via to may at) with a report of every unmapped construct"
type = "story"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-09T04:35:31Z"
updated = "2026-10-09T04:35:31Z"
labels = ["adoption:logand-app", "grimble"]
scope = ["crates/grimble/**", "crates/grimble-model/**", "changelog.d/**"]

[[acceptance]]
text = "Given a v1 design/*.strata model with code, attr interface, may ... via and a construct with no v2 equivalent, when grimble migrate runs, then design/*.grmb is written, grimble check loads it, and the report lists each semantic change and each dropped construct"
bound = false
+++

Designed in docs/design/migration.md (row design/*.strata) but unimplemented. Requested by the logand.app-v2 migration (hand-written logand-app.strata and generated vmodel.strata feeding v1 sys audit and SYS100 ceilings).
