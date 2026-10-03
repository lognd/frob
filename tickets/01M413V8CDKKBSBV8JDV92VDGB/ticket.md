+++
id = "01M413V8CDKKBSBV8JDV92VDGB"
title = "check --ticket leads with findings in the ticket's diff and summarises the rest as counts"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-03T14:49:15Z"
updated = "2026-10-03T18:18:32Z"
scope = ["crates/frob-check/**", "crates/frob/src/check_cmd.rs"]

[[acceptance]]
text = "Given a ticket diff touching one file and repository-wide warnings elsewhere, when check --ticket --text runs, then findings on the touched file print first and the others appear only as per-rule counts"
bound = false

[[acceptance]]
text = "Given --json, when check --ticket runs, then every finding is still present"
bound = false
+++

Reported by mdcat (FROB_FEEDBACK item 3): on a fresh fork, check --ticket printed about 50 COV001/DOC001 warnings on untouched files plus 'opaque text file' unresolved notes, burying the one finding that mattered. In --ticket mode, text output lists findings on paths in the ticket's diff first, then one count line per rule for the rest (full list under -v and in JSON, which is unchanged). Also check why 2031 files count as opaque in mdcat (fixtures or build output walked?) and file a follow-up if the walk is wrong.
