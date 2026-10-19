//! The PACK rule pages of `src/pack_rules/*.md` as an mdtest corpus.

// frob:ticket 01M3ZX7K3N8AWVBTZ90E0F1YSP

mod common;

use gob_rules::{Finding, Severity};
use grimble_capabilities::pack_rules::evaluate;

/// Run the pack pass over a `pack` example and keep the findings of the rule under test.
fn runner(case: &gob_mdtest::Case) -> Vec<Finding> {
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack001.rs::Pack001
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack002.rs::Pack002
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack003.rs::Pack003
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack004.rs::Pack004
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack005.rs::Pack005
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack006.rs::Pack006
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack007.rs::Pack007
    // frob:tests crates/grimble-capabilities/src/pack_rules/pack008.rs::Pack008
    let inp = common::parse(&case.text);
    let required = case.text.contains("required");
    evaluate(inp.lock.as_ref(), &inp.packs, &inp.issues)
        .into_iter()
        .filter(|f| f.rule == case.rule)
        .map(|mut f| {
            // The harness fire control rejects Unresolved; a required one fails the gate, so show it as Error.
            if required && f.severity == Severity::Unresolved {
                f.severity = Severity::Error;
            }
            f
        })
        .collect()
}

gob_mdtest::mdtest!(dir = "src/pack_rules", runner = runner);
