+++
id = "01M6Z15WBQCQDYSHC0HSXJJYWH"
title = "crunk-rules: read LAYOUT001/002 and RESP001 from crunk-layout solver output, not crunk-ingest scene.json"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-09T02:11:14Z"
updated = "2026-11-09T02:36:24Z"

[[acceptance]]
text = "LAYOUT001/002 consume crunk-layout solver output via the scene_docs facts (RESP001 split to a follow-up)"
bound = true

[[acceptance]]
text = "The crunk-layout corpus test uses the shared crunk_layout::findings functions the rules call, with the duplicated overlap/containment code deleted"
bound = true

[[acceptance]]
text = "Existing crunk-rules tests keep passing"
bound = true
+++
