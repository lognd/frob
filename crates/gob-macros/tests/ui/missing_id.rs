use gob_rules::Rule;

/// Doc.
#[derive(Rule)]
#[rule(slug = "x-rule", family = "XRL", severity = Error, tier = Lang, scope = File, fix = Manual, version = 1)]
struct R;

fn main() {}
