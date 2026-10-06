+++
id = "01M47QKVBB5G9N1QZP3AVXTRHX"
title = "gob-frameworks: framework registry, per-workspace detection, react-router and Next.js routes"
type = "story"
category = "todo"
priority = "high"
points = 8
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T04:30:11Z"
updated = "2026-10-06T04:30:11Z"
scope = ["crates/gob-frameworks/**", "Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "a Next.js fixture and a react-router fixture produce the expected routes snapshot"
bound = false

[[acceptance]]
text = "detection finds a framework in a workspace member below the root"
bound = false

[[acceptance]]
text = "a route whose path is not statically known is reported with status Unknown, not omitted"
bound = false
+++

language-engines.md section 4. New crate crates/gob-frameworks above gob-symbols and below every product. Framework is an open inventory registry; detection by package.json dependency, config file or directory convention, evaluated per workspace member, never the repository root only (~5E0V6W3). Answers: routes (path pattern, method, handler unit, page component, layout chain, each with status) and entrypoints. First adapters: react-router (route objects and JSX Route elements via const_value) and Next.js app and pages directories. Supersedes ~XPMQ50D; the crunk-adapters crate is not created.
