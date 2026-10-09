+++
id = "01M4FD0TNGWDEYHP9FHH0RPXYR"
title = "frob:describes in docs: the doc-side half of the doc-code pair (doc-consistency.md), parsed and paired with frob:doc for DRIFT001"
type = "story"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T03:58:57Z"
updated = "2026-10-09T05:26:08Z"
labels = ["adoption:hullbreach", "creates:crates/gob-directives/tests/describes.rs"]
scope = ["changelog.d/**", "crates/gob-directives/src/frob.rs", "crates/gob-directives/tests/describes.rs", "crates/frob-ack/src/inputs.rs", "crates/frob-ack/tests/ack.rs", "crates/frob-check/src/snapshot.rs", "docs/reference/directives.md", "docs/schemas/directives.json"]

[[acceptance]]
text = "Given a markdown doc with <!-- frob:describes src/x.py::Sym --> and no code-side frob:doc, when frob check runs, then the pair is formed and DRIFT001 fires when either side changes until acked"
bound = false
+++

Designed in doc-consistency.md but unimplemented (DSL001 today). Hullbreach platform has 61 uses.
