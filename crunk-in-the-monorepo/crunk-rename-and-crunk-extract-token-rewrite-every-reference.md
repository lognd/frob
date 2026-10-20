+++
id = "01M4CXRB2DX0B0BW7YJPAN1YXT"
title = "crunk rename and crunk extract-token rewrite every reference"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-08T04:53:42Z"
updated = "2026-10-08T04:53:42Z"
scope = ["changelog.d/**", "crates/crunk/**", "crates/crunk-spec/**"]

[[acceptance]]
text = "Given a token used in CSS, TSX and specs, when renamed or extracted, then every reference is rewritten and crunk check is clean"
bound = false
+++

docs/design/crunk.md section 5.
