+++
id = "01M55VA2JGWG99548QNW3T58PK"
title = "Move DIGEST_SCHEME to gob-caps; gob-lock and gob-ir duplicate the literal"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T21:11:58Z"
updated = "2026-10-27T02:58:21Z"
scope = ["crates/gob-lock/**"]
+++

found while working ~NF2ZMQG: gob-lock literal 2 guarded only by an equality test in crates/frob-ack/tests/ack.rs.
