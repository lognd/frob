+++
id = "01M43ARYFVG86PAGGM78JGRZY3"
title = "crunk-ingest: map JSX style props and className class_tokens into ProjectStyles"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:49Z"
updated = "2026-10-08T10:22:18Z"
idempotency_key = "crunk-plan-jsx"
labels = ["area:crunk", "creates:crates/crunk-ingest/src/jsx/**"]
scope = ["crates/crunk-ingest/src/jsx/**", "crates/crunk-ingest/tests/jsx*.rs", "crates/crunk-ingest/src/model.rs", "crates/crunk-ingest/src/lib.rs", "crates/crunk-ingest/src/walk.rs", "crates/crunk-ingest/Cargo.toml", "crates/crunk-ingest/tests/fixtures/**", "crates/crunk-ingest/tests/common/**"]

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[links]]
kind = "blocked-by"
target = "01M43ARXVD5PXP6ZBVFC2F4ZMQ"

[[links]]
kind = "blocked-by"
target = "01M43ARY26XF7A4MSRAZ8V73JM"

[[links]]
kind = "blocked-by"
target = "01M43ARY91XZ35DN9SCHRHS033"

[[links]]
kind = "blocked-by"
target = "01M47QKSBYX7YFQHV3VVGKB025"

[[acceptance]]
text = """Given `<div style={{ margin: '13px' }} className="p-[7px] " + x>`, when ingested, then the style declaration and the static class fragment are produced and the dynamic part is flagged"""
bound = true

[[acceptance]]
text = "Given the web_pages fixture, when ingested, then the extracted sites equal the Python output"
bound = true

[[acceptance]]
text = "Given a style-prop site, when a fix is requested later, then it is marked not fixable"
bound = true
+++

Port ingest/jsx (_ast, _classnames, _style, _consts, _tokens; sits on the TS adapter and consteval): style-prop declarations go through the same rules but are never auto-fixed; computed classNames only scanned in static fragments. Port tests/unit/test_ingest_jsx.py and INT-11.
