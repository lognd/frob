+++
id = "01M4FCZT2N5WN3VPVJ8KB92Z06"
title = "v1 importer: accept CRLF front matter, default to all tickets, keep v1 sprint as a sprint:<v> label"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T03:58:24Z"
updated = "2026-10-10T20:27:19Z"
labels = ["adoption:hullbreach"]
scope = ["crates/gob-dev/**", "docs/guides/upgrade-from-v1.md", "changelog.d/**"]

[[acceptance]]
text = "Given a v1 repository with CRLF ticket files and sprint fields and no selection file, when the importer runs, then every ticket imports, each sprint becomes a sprint:<value> label, and the guide documents the defaults"
bound = true
+++

Hullbreach platform repros: missing opening fence on CRLF tickets (core.autocrlf=true); default --selection is frob's own file (ENOENT elsewhere); 116 of 130 tickets lose their sprint.
