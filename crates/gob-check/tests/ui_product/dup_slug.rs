//! A duplicate slug across two crates of one product is a compile error naming both.

use gob_rules::{RuleDef, RuleIndex};

macro_rules! rule_crate {
    ($name:ident, $krate:literal, $id:literal, $slug:literal, $retired:expr) => {
        mod $name {
            pub mod rules {
                use gob_rules::{BoundRule, RuleDef, RuleIndex};

                pub const DEF: RuleDef = RuleDef {
                    id: $id,
                    slug: $slug,
                    file: "src/rules/x.rs",
                    line: 7,
                    ..RuleDef::POISONED
                };
                pub const INDEX: RuleIndex = RuleIndex {
                    krate: $krate,
                    metas: &[&DEF],
                    renamed: &[],
                    retired: $retired,
                };

                pub fn bind<P: ?Sized + 'static>() -> Vec<BoundRule<P>> {
                    Vec::new()
                }
            }
        }
    };
}

rule_crate!(first, "first-rules", "COV001", "same-slug", &[]);
rule_crate!(second, "second-rules", "COV002", "same-slug", &[]);

gob_check::product_rules! {
    product = Demo;
    host = ();
    crates = [first, second];
}

fn main() {
    let _: Option<(RuleDef, RuleIndex)> = None;
}
