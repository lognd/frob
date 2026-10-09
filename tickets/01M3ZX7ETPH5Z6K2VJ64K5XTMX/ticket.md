+++
id = "01M3ZX7ETPH5Z6K2VJ64K5XTMX"
title = "Plan executor core: find, where, containment, position, three-valued connectives"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-09T06:09:31Z"
idempotency_key = "m2-exec-core"
labels = ["milestone:2", "area:grl", "creates:crates/gob-plan/src/exec/mod.rs", "creates:crates/gob-plan/tests/exec_core.rs", "creates:crates/gob-plan/tests/support/**"]
scope = ["crates/gob-plan/src/exec/core/**", "crates/gob-plan/src/exec.rs", "crates/gob-plan/src/lib.rs", "crates/gob-plan/tests/web_rule.rs", "crates/gob-plan/Cargo.toml", "crates/gob-plan/README.md", "crates/gob-plan/src/exec/mod.rs", "crates/gob-plan/tests/exec_core.rs", "crates/gob-plan/tests/support/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EG6S2V48F43HP1GM2NQ"

[[links]]
kind = "relates"
target = "01M3ZTAV8SXD9C6G4A42WY14K9"

[[acceptance]]
text = "Given a plan `find f: function where f is public` and a gob-ir fixture, when executed, then bindings are the public functions in (path, offset) order"
bound = true

[[acceptance]]
text = "Given `a inside b` and `a directly inside b` over nested statements, when executed, then the first looks through any depth and the second one level, and a property test confirms the Kleene truth tables for not/and/or/any"
bound = true

[[acceptance]]
text = "crates/gob-plan/src/exec.rs (the temporary web-kind executor) is deleted and crates/gob-plan/tests/web_rule.rs passes on the general executor"
bound = true
+++

Implements grl-spec.md sections 7.1 and 7.2; plugins.md section 6; universal-model.md section 4.

Run plans over gob-ir with the Kleene evaluator: binding order, fields, inside/has transitive versus directly, before/after/adjoins, not/and/or/any.
