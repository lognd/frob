+++
id = "01M3WYJ8070P06AN3YYSFBR9ZG"
title = "gob-log: tracing setup, FROB_LOG, redaction"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0007"]
labels = ["milestone:2.0.0", "component:gob-log"]
scope = ["crates/gob-log/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ803SJM87D7TS77Y40A4"

[[acceptance]]
text = "Given FROB_LOG=gob_git=debug, when init runs, then only gob_git debug events are emitted"
bound = false

[[acceptance]]
text = "Given a transcript containing a GitHub token and an AWS key, when redacted, then both are masked and the rest is unchanged"
bound = false
+++

Implement crates/gob-log per architecture.md section 5 and D37/M24. Provide init(product, verbosity, json: bool) building a tracing-subscriber with EnvFilter from FROB_LOG (documented as the one diagnostic env var), human or JSON layer to stderr, span timing for commands; a redact(text) function that masks common secret shapes (bearer tokens, AWS keys, GitHub tokens ghp_/github_pat_, URLs with userinfo, KEY=VALUE where KEY matches *TOKEN*|*SECRET*|*PASSWORD*) for use by evidence capture and telemetry; a test-only subscriber capture helper. Rustdoc notes that products never println outside renderers.
