+++
id = "01M4D6NSC2DP2P09F4QTR723S3"
title = "frob lease release: give up a finished-but-unlanded ticket's lease without requeue"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:35Z"
updated = "2026-10-08T07:29:35Z"
scope = ["changelog.d/**", "crates/frob-lease/**", "crates/frob/**"]

[[acceptance]]
text = "Given a committed ticket with evidence, when lease release runs, then the lease is freed and a later land re-takes it"
bound = false
+++

Follow-up from ~RF60RCZ/~57FX1J2: overlapping scopes forced requeue and re-lease dances before landing.
