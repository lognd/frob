+++
id = "01M35RZY8A430GX9CD3123KZE4"
title = "Wire css/scss into capability/dup/docblock FACETS"
type = "story"
flavour = "quality_objective"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5386"]
labels = ["v1-cluster:D2"]
scope = ["src/frob/lang/_support.py"]
+++

found while working T-5303: css/scss grammars are wired into frob.lang (_EXTENSION_TABLE, _walk_css.py) but not yet into the capability/dup/docblock FACETS registry (_support.py's _PENDING_FACET_WIRING_TICKETS), mirroring zig's T-3513 precedent
