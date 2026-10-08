+++
id = "01M4D6NXRHA7NH42PB67TH24RC"
title = "Decide frob-gh: wire it in (mirror, CI) or remove it (audit M11)"
type = "task"
category = "todo"
priority = "low"
points = 1
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:40Z"
updated = "2026-10-08T07:29:40Z"
scope = ["changelog.d/**", "crates/frob-gh/**", "Cargo.toml"]

[[acceptance]]
text = "Given the decision, when recorded, then frob-gh is either consumed or deleted with a dropped-ticket note"
bound = false
+++

~GHMWDGG chose frob-release::ci over frob-gh; frob-gh has no consumer.
