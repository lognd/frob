#![deny(deprecated)]

use gob_rules::Rule;

/// Doc.
#[derive(Rule)]
#[rule(id = "XRL001", slug = "x-rule", family = "XRL", severity = Error, tier = Lang, scope = File, fix = Manual, polarity = Pplus, must_measure = false, version = 1)]
struct R;

fn main() {}
