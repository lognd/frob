+++
id = "01M43AVMZGQ4JYB8QYWAYA6294"
title = "First crunk preview release from this repository"
type = "story"
category = "todo"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:17Z"
updated = "2026-10-04T11:30:17Z"
idempotency_key = "crunk-plan-release"
labels = ["area:crunk"]
scope = ["frob.toml", "changelog.d/**", "docs/crunk/release.md"]

[[links]]
kind = "blocked-by"
target = "01M43ARWCVRCE25KDZC8CRC1ZH"

[[links]]
kind = "blocked-by"
target = "01M43ARWKFWVZZAR84NF50FAHB"

[[links]]
kind = "blocked-by"
target = "01M43AVKMT52QCG7DGNQ4J906S"

[[links]]
kind = "blocked-by"
target = "01M43AVMAY5VB8K1885CDYEYV6"

[[acceptance]]
text = "Given the milestone, when `frob release status` runs, then every criterion is bound and ready"
bound = false

[[acceptance]]
text = "Given the cut, when tags are listed, then crunk-v<version> exists beside frob and grimble tags at the same commit"
bound = false

[[acceptance]]
text = "Given `uv tool install frob` on a clean machine, when run, then crunk is installed beside frob and `frob doctor` finds it"
bound = false
+++

Cut the milestone that ships crunk (see the planner's milestone proposal): milestone object and exit criteria, the `crunk-v` tag through `frob release cut`, wheels and archives smoke, `frob` wheel depends on crunk at the same version, release notes stating that PyPI crunk continues from here and that the Python releases stop at the switch. Keep crunk in [release] preview until the retirement tickets below close.
