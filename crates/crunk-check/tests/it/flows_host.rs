//! `CrunkInputs` hands the collected flow files to the rules as `CrunkHost::flows`.

// frob:ticket 01M7HC8TXG8C5YBWXB8FP71BSA

use crunk_check::CrunkInputs;
use crunk_rules::CrunkHost;
use crunk_rules::flow_files::FlowFacts;

// frob:tests crates/crunk-check/src/product.rs::CrunkInputs.flows
#[test]
fn collected_flow_facts_are_served_through_the_host() {
    let inputs = CrunkInputs {
        flows: Some(FlowFacts::default()),
        ..CrunkInputs::default()
    };
    assert!(CrunkHost::flows(&inputs).is_some());
}

// frob:tests crates/crunk-check/src/product.rs::CrunkInputs.flows
#[test]
fn no_flow_facts_means_the_host_serves_none() {
    assert!(CrunkHost::flows(&CrunkInputs::default()).is_none());
}
