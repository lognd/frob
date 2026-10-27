+++
id = "01M5XCWXYNXW0RW8VRDQPY31M6"
title = "Solver style mapping: resolved scene CSS to taffy styles (block, flex wrap both ways, grid tracks and spans, absolute, gap, padding, min/max, aspect-ratio) with token var() resolution"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-27T00:41:53Z"
updated = "2026-10-27T00:45:27Z"
labels = ["area:crunk"]
scope = ["crates/crunk-layout/src/style/**, crates/crunk-layout/tests/style*.rs", "crates/crunk-layout/Cargo.toml"]

[[acceptance]]
text = "Given each supported property, when mapped, then the taffy Style equals the expected value. Edge cases: min-width greater than max-width resolves to min (CSS rule); a percentage size under an indefinite parent is treated as auto; aspect-ratio with both width and height set ignores the ratio; a grid span past the last explicit track creates implicit tracks; flex-wrap wrap-reverse on column direction; absolute inset on two opposing sides with no size stretches; negative padding or gap is a finding not a panic; var(--x) with an undefined token yields a typed error naming the element and line; display:none removes the node from layout but keeps its data-id in the output as hidden"
bound = false
+++

Design crunk.md section 3. New module in crunk-layout depending on crunk-scene and taffy (pin the version in the workspace). Input is the parsed scene plus resolved tokens; output is a taffy tree keyed by data-id. No text measurement here (text nodes take a measure hook supplied by the text ticket). Result-returning, no unwrap in non-test code.
