+++
id = "01M48MR4V68JMFW44NG67J8R53"
title = "Replace link-time inventory anchors with an explicit per-product registry checked against inventory"
type = "story"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T12:59:20Z"
updated = "2026-10-06T13:14:12Z"
scope = ["crates/gob-rules/**", "crates/gob-dev/**", "crates/gob-config/**", "crates/gob-cli/**"]

[[acceptance]]
text = "a product whose rule crate is dropped from the build fails the registry test naming the missing crate"
bound = false

[[acceptance]]
text = "duplicate ids and slugs fail at test time with both declaring modules named"
bound = false

[[acceptance]]
text = "renamed rule ids resolve through a redirect table and old ids in config and directives keep working"
bound = false

[[acceptance]]
text = "gob-dev has no link anchor code"
bound = false

[[acceptance]]
text = "a removed rule keeps its id reserved (a new rule reusing it fails), and no live id or slug is shadowed by a redirect (test)"
bound = false

[[acceptance]]
text = "a source scan fails naming any derive(Rule) type that is not in its product's registry"
bound = false
+++

Macro review 2026-10-06: rule, table, command, directive and artifact registration is link-time (inventory), so a product crate that is not linked contributes nothing silently; gob-dev already needs an anchor (link_inventories touches crunk_spec::OWN_TABLES.len()) to keep crunk's entries alive, and duplicate rule ids are only found at runtime. ruff keeps one reviewed table per linter (the map_codes attribute over codes.rs) so codes are exhaustive and unique at compile time and renames go through a redirect table. Keep inventory (D76 plugins are logically identical to built-ins) but have each product declare its registry crates in one place (a generated or macro-declared list), with a test that the inventory contents equal that list (nothing missing, nothing extra, no duplicate id or slug), and a rename/redirect table for rule ids and slugs. Remove the anchor hack.
