+++
id = "01M418CXCED7DEBX4WV2PM2R2K"
title = "frob:accept CI006 in a YAML comment does not suppress the zizmor finding"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T16:08:48Z"
updated = "2026-10-03T18:17:32Z"
labels = ["area:check"]
scope = ["crates/gob-languages/src/language.rs", "crates/gob-languages/src/grammar.rs", "crates/gob-symbols/src/yaml.rs", "crates/gob-symbols/src/registry.rs", "crates/gob-symbols/src/lib.rs", ".github/workflows/dev.yml", "frob.lock", "docs/reference/fidelity.md", "crates/frob-check/**", "crates/frob-obligations/**", "crates/gob-directives/**"]

[[acceptance]]
text = "Given a frob:accept CI006 comment directly above the on: key of a workflow, when frob check runs, then the CI006 finding is suppressed and the accept is listed"
bound = true
+++

found while working ~NE8Z036.

Repro (repository at the ticket/NE8Z036 worktree, dev.yml as committed):
1. In .github/workflows/dev.yml replace the line 'on: # zizmor: ignore[dangerous-triggers]' with two lines: '# frob:accept CI006 because="workflow_run gated by the plan job on a successful push run of this repository"' directly above 'on:'.
2. Run: frob check (repo binary target/debug/frob).
3. Expected: the CI006 zizmor/dangerous-triggers finding at dev.yml (the on: line) is suppressed by the accept, as the test a_frob_accept_suppresses_a_tool_finding_like_a_native_one suggests for tool findings.
4. Actual: '.github/workflows/dev.yml:15:1: error CI006 zizmor/dangerous-triggers' is still reported and no EXC finding appears, so the directive is either not scanned in YAML files or not bound to the on: key. Same result with the comment on the same line as on:.
Workaround in use: an inline zizmor ignore comment on the on: line.
