use gob_rules::Rule;

/// Doc.
#[derive(Rule)]
#[rule(id = "XRL001", slug = "x-rule", family = "XRL", severity = Error, polarity = Sideways, tier = Lang, scope = File, fix = Manual, version = 1)]
struct R;

fn main() {}
