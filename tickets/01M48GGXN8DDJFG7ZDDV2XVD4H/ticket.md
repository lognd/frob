+++
id = "01M48GGXN8DDJFG7ZDDV2XVD4H"
title = "gob-frameworks: remove unused insta dev-dependency (cargo shear fails ci)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T11:45:25Z"
updated = "2026-10-06T11:45:25Z"
scope = ["crates/gob-frameworks/Cargo.toml", "Cargo.lock"]
+++

cargo dev ci step shear fails: unused dependency insta in crates/gob-frameworks/Cargo.toml. Found while working ~4M1BX5H.
