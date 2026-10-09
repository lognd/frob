+++
id = "01M4GK56B7ADTTC87X31CR03NE"
title = "Upgrade guide: recipe for merging v2 main into a v1 branch (ticket tree rename conflicts: take main's tickets/ tree, or git merge -X no-renames)"
type = "docs"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-09T15:05:26Z"
updated = "2026-10-09T15:05:26Z"
labels = ["adoption:logand-app"]
scope = ["docs/guides/upgrade-from-v1.md", "changelog.d/**"]

[[acceptance]]
text = "Given a v1 branch and v2 main, when a reader follows the guide's recipe, then the merge resolves with main's tickets/ tree and no ticket data is lost; the importer report points at the recipe"
bound = false
+++

logand.app-v2 F-547: about 600 ticket file conflicts from rename detection pairing v1 done-report.md with v2 events/*.toml.
