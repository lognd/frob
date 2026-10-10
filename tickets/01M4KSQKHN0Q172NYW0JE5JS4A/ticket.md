+++
id = "01M4KSQKHN0Q172NYW0JE5JS4A"
title = "docs/migration/v1-import.md still lists sprint as a dropped v1 field after ~KB92Z06 carries it as a sprint:<v> label"
type = "docs"
category = "todo"
priority = "medium"
points = 1
reporter = "Claude"
created = "2026-10-10T20:58:04Z"
updated = "2026-10-10T20:58:04Z"
scope = ["docs/migration/v1-import.md", "changelog.d/**"]

[[acceptance]]
text = "Given docs/migration/v1-import.md, when this lands, then the dropped-fields table has no sprint row and the mapping table lists sprint as the label sprint:<v>"
bound = false
+++

found while landing ~KB92Z06: the page is historical, hand-kept output of the importer report, not covered by gen all --check
