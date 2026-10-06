+++
id = "01M43ATASM383KB9130JY79XVV"
title = "crunk-rules: rule registry, family metadata, waivers and WAIVE001"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:29:34Z"
updated = "2026-10-06T13:56:21Z"
idempotency_key = "crunk-plan-rfw"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**", "crates/crunk-check/src/rules.rs", "docs/crunk/rules/**", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43ARVS24254G85TMFYH8FGQ"

[[links]]
kind = "blocked-by"
target = "01M43ARX764095Q4VWABWXXV5H"

[[links]]
kind = "blocked-by"
target = "01M43ARY26XF7A4MSRAZ8V73JM"

[[acceptance]]
text = "Given a rule declared with the derive, when the registry is listed, then id, family, default severity, fixable flag and doc appear and `cargo dev gen --check` is clean"
bound = false

[[acceptance]]
text = "Given `crunk:waive COLOR001` with no reason, when checked, then WAIVE001 fires and COLOR001 is not suppressed"
bound = false

[[acceptance]]
text = "Given findings from several files, when reported, then order is (path, line, rule)"
bound = false
+++

Rust tier-0 rule framework: `#[derive(Rule)]` registry (gob-rules, gob-macros) replaces the hand-written dict and assert against RULE_IDS (rules/engine.py, models.py); crunk families registered under the crunk namespace so frob never sees COLOR001 as an unknown gate id (the GATERULE001 complaint, monorepo.md 3); `[lint]` severities and tolerances as config; `crunk:waive RULE reason="..."` through gob-directives namespace crunk plus WAIVE001 (_waive.py); output sorted (path, line, rule) (INV-005); generated rule pages in docs/crunk/rules (GEN001). Why Rust: see the epic body; GRL has no CSS declaration kind or value-domain operators yet. Port tests/unit/test_rules_engine.py and INT-03 shape.
