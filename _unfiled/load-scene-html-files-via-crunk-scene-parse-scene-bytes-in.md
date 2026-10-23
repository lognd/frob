+++
id = "01M5H30AT7FM2BAXCTTDEGWV6J"
title = "Load .scene.html files via crunk-scene::parse_scene_bytes in crunk-ingest/crunk-check scene discovery"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T05:58:06Z"
updated = "2026-10-23T06:15:19Z"
scope = ["crates/crunk-ingest/**", "crates/crunk-check/**", "crates/crunk-scene/**", "Cargo.lock"]

[[acceptance]]
text = "a .scene.html file in a project is discovered and loaded through crunk_scene::parse_scene_bytes by crunk-ingest"
bound = false

[[acceptance]]
text = "crunk-check scene discovery includes .scene.html files and reports parse failures as findings"
bound = false
+++
