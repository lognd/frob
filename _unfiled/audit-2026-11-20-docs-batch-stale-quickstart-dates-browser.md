+++
id = "01M7X35SWWSG5ZB79424FA4PC8"
title = "Audit 2026-11-20 docs batch: stale quickstart dates, browser-render setup, dead links, overclaiming fragment"
type = "docs"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-20T18:23:22Z"
updated = "2026-11-20T18:23:22Z"
scope = ["docs/**", "changelog.d/**"]

[[acceptance]]
text = "Given the quickstart, when a reader copies the cycle command today, then the cycle contains today and doc_commands still passes"
bound = false

[[acceptance]]
text = "Given docs/guides/crunk.md, when a reader wants browser rendering, then it names the gallery feature, the Playwright and axe install steps and the exit codes of render"
bound = false
+++

Findings: quickstart.md:81-85 literal Oct dates; crunk.md:43 no browser setup; fragment 01M4CXRV40WWJQKHWJJBKJT1HZ overclaims phase 5; crunk-from-python.md:48, crunk-hullbreach.md:83, crunk.md:328 say Playwright not ported; CHANGELOG.md:9 dead link (docs/migration/upgrade-from-v1.md); quickstart assumes bash and hand-substituted handle; README first-look next step; frob-docgen help text; crunk render scene-missing error hint.
