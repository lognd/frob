+++
id = "01M5XWCAYVZQX363SSWYCR4M6H"
title = "CAP: method calls on typed receivers (ureq::Agent) are not detected as net.connect"
type = "bug"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T05:12:27Z"
updated = "2026-10-29T01:39:37Z"
scope = ["crates/gob-ir/src/registry.rs", "crates/grimble-bind/src/caps.rs", "crates/grimble-bind/tests/**", "crates/grimble-bind/Cargo.toml", "Cargo.lock", "design/model.grmb"]

[[acceptance]]
text = "ureq::Agent get/post calls in crates/frob-mirror/src/github/http.rs are observed as net.connect and either granted narrowly or fire CAP001"
bound = true
+++

Follow-up of KEM2RHP: the vocabulary matches by path spelling, so methods on Agent receivers are invisible.
