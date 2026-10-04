+++
id = "01M43ARVJKKN4EXCQF1NRTJ3KW"
title = "crunk-values: Color, Length, WCAG contrast and palette distance"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:46Z"
updated = "2026-10-04T11:43:19Z"
idempotency_key = "crunk-plan-vals"
labels = ["area:crunk"]
scope = ["crates/crunk-values/**", "Cargo.lock"]

[[acceptance]]
text = "Given the Python test vectors for hex, rgb() and hsl() literals, when parsed, then the sRGB values equal the Python results and malformed literals return a typed error"
bound = true

[[acceptance]]
text = "Given two colors, when the weighted-sRGB distance and the WCAG contrast ratio are computed, then they match the Python crunk to 1e-9"
bound = true

[[acceptance]]
text = "Given a length in rem, px or em with a root font size, when converted, then the px value matches the Python crunk and an unknown unit returns a typed error"
bound = false
+++

Port crunk.values (520 LOC: hex/rgb/hsl parse, weighted-sRGB distance, WCAG luminance and contrast ratio, Length with rem/px) to a pure crate with no gob dependency beyond thiserror/tracing; results are typed errors, no panics. docs/design/boundaries.md 2.4 (crunk_values). Port tests/unit/test_values.py. OKLab/OKLCH (v1 T-0075, T-0079) is out of scope.
