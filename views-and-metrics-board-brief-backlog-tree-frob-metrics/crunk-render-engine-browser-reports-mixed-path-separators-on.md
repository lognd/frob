+++
id = "01M7WPS02K6P6F2K3RQBCG9A27"
title = "crunk render --engine browser reports mixed path separators on Windows"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-20T14:46:39Z"
updated = "2026-11-20T14:46:52Z"

[[acceptance]]
text = "Given a Windows run of crunk render --engine browser, when the JSON data lists each cell's png, boxes and path, then every reported path uses only forward slashes"
bound = false
+++

Found while closing ~WPZ2BDG: the reported paths look like .crunk/render\clean\default\chromium-desktop.png, a forward-slash base joined with backslash components. Start in crates/crunk/src/render_browser.rs: browser_paths joins through posix(), but the cell path comes from another join. Fix at the join, and pin it with a test that asserts no backslash in any reported path.
