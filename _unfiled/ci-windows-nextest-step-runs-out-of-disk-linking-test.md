+++
id = "01M6VYQYX4EBQTWGTR81JC3PFH"
title = "CI Windows nextest step runs out of disk linking test binaries (LNK1180)"
type = "bug"
category = "in-progress"
priority = "critical"
class = "expedite"
reporter = "lognd"
created = "2026-11-07T21:30:58Z"
updated = "2026-11-07T21:31:07Z"
labels = ["ci"]
scope = [".github/workflows/ci.yml", ".github/actions/**"]

[[acceptance]]
text = "given the CI rust windows-latest job, when the nextest step builds and runs all tests, then it finishes without a disk-space link error"
bound = false
+++

Run 42412121808 rust (windows-latest): nextest failed after 1562s with LNK1180 insufficient disk space; the runner had 40 MB free. Free space or shrink test artifacts before or during the test build without skipping any test.
