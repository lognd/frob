+++
id = "01M5B3C8W6AG0G7K53KK75B3D3"
title = "frob:doc in no-grammar files is skipped by frob-ack (extend lexical directive scan)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T22:09:11Z"
updated = "2026-10-19T23:02:34Z"
scope = ["crates/frob-ack/src/inputs.rs"]

[[acceptance]]
text = "frob:doc in a no-grammar file is collected by frob-ack"
bound = true
+++

found while working ~GCNECVB: crates/frob-ack/src/inputs.rs:190 skips Language::detect==None files, so frob:doc there is ignored. Use Scanner::scan_unparsed_in.
