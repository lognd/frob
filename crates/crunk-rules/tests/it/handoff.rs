//! The handoff standing words.

// frob:ticket 01M7TBK44G9J6HCMEXFWA6AW81

use crunk_rules::handoff::Standing;

// frob:tests crates/crunk-rules/src/handoff.rs::Standing.word
#[test]
fn each_standing_names_its_status_word() {
    assert_eq!(Standing::Draft.word(), "draft");
    assert_eq!(Standing::Ready.word(), "ready");
    assert_eq!(Standing::Changed.word(), "changed");
}
