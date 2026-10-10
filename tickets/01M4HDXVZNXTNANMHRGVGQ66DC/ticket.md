+++
id = "01M4HDXVZNXTNANMHRGVGQ66DC"
title = "Rule and atom ramp-in: a rule or atom that becomes live in a new release enters at Warn for one release (configurable), and each release and global refresh lists newly live rules and atoms"
type = "story"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T22:53:18Z"
updated = "2026-10-09T22:53:18Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-rules/**", "crates/frob-release/**", "changelog.d/**"]

[[acceptance]]
text = "Given a rule or capability atom first shipped in release N, when a repository checks with release N, then its findings are Warn with a note naming the release where they become their declared severity (N+1), unless [rules] ramp = false"
bound = false

[[acceptance]]
text = "Given a release or dev build, when its notes are generated, then newly live rules and atoms are listed in a dedicated section"
bound = false
+++

logand.app-v2 F-573 wish 1. R1 synthesis C35 already recommends new rules ship Advisory and graduate by ratchet.
