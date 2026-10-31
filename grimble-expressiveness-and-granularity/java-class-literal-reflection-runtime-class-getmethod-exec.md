+++
id = "01M68B54QSJ9VSZ6S1SZYJNFX1"
title = 'Java class-literal reflection (Runtime.class.getMethod("exec")) is a silent pass'
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T06:43:04Z"
updated = "2026-10-31T08:10:30Z"
scope = ["crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "crates/grimble-check/tests/symbolic_audit.rs", "changelog.d"]

[[acceptance]]
text = 'Java Runtime.class.getMethod("exec", String.class).invoke(o, "x") reports a CAP001 (certain process.spawn or Unresolved), never clean'
bound = true

[[acceptance]]
text = "A probe in symbolic_audit.rs covers it with a shadowed-type clean control"
bound = false
+++

Found while working ~TFZAPQN: a class literal (X.class) is not a use, so reflection on a capability class goes unreported. Symbolic fix: resolve class_literal types in java_uses.
