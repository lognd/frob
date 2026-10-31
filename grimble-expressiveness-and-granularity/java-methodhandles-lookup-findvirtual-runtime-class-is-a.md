+++
id = "01M68B54TJ3MNW1AHNQEV1AJCV"
title = "Java MethodHandles.lookup().findVirtual(Runtime.class, ...) is a silent pass"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T06:43:04Z"
updated = "2026-10-31T08:31:17Z"
scope = ["crates/gob-symbols/**", "crates/gob-caps/**", "crates/grimble-bind/**", "crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "Java java.lang.invoke MethodHandles lookup findVirtual/findStatic/findConstructor on a capability class reports a CAP001 (certain or Unresolved), never clean"
bound = true

[[acceptance]]
text = "A probe in symbolic_audit.rs covers it with a shadowed-type clean control"
bound = false
+++

Found while working ~TFZAPQN: java.lang.invoke method-handle reflection is absent from the java code.eval vocabulary.
