+++
id = "01M4GWHE6JBZMC08ZS6W1VYNKJ"
title = "Warn when config or tool-stage scripts name a git branch that no longer exists (e.g. after land deletes it); consider a [land] after hook"
type = "story"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-09T17:49:24Z"
updated = "2026-10-09T17:49:24Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-check/**", "crates/frob-land/**", "changelog.d/**"]

[[acceptance]]
text = "Given a tool stage command or frob.toml value naming refs/heads/X and X deleted by land, when frob check runs, then a warning names the stage and the missing branch instead of the stage failing opaquely"
bound = false
+++

logand.app-v2 F-564 (wish): a vmodel script hard-coded a branch that land then deleted; the stage went red main-wide.
