+++
id = "01M6MFRWAC9RC1KQ9GD45QPGT1"
title = "COV001: macro argument naming an item is an Error, should be Unresolved (opaque region)"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-04T23:54:38Z"
updated = "2026-11-04T23:54:38Z"
labels = ["no-story"]
scope = ["crates/frob-obligations/src/cov.rs"]
+++

Found while working ~C3AMTNM: in the polarity corpus an opaque macro body 'unexpanded!(target)' that names a pub fn without a call syntax makes COV001 emit Error (reached by no test), but the macro may expand to a call (Theorem 3). Make COV001 answer Unresolved naming the macro when a test holds an unexpanded macro mentioning the item, then add the repo to crates/frob-obligations/tests/polarity_conformance.rs.
