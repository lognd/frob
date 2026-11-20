//! The handoff standing words.

// frob:ticket 01M7TBK44G9J6HCMEXFWA6AW81
// frob:ticket 01M7TCKMBT95HKXRACWVH5VVDY

use crunk_rules::handoff::{Reason, Standing};

// frob:tests crates/crunk-rules/src/handoff.rs::Standing.word
#[test]
fn each_standing_names_its_status_word() {
    assert_eq!(Standing::Draft.word(), "draft");
    assert_eq!(Standing::Ready.word(), "ready");
    assert_eq!(Standing::Changed.word(), "changed");
}

// frob:tests crates/crunk-rules/src/handoff.rs::Reason.line
#[test]
fn each_reason_describes_itself_in_one_line() {
    assert_eq!(
        Reason::BlockingComment("c1".into()).line(),
        "open blocking comment `c1`"
    );
    assert_eq!(
        Reason::StaleExport("tokens.css".into()).line(),
        "stale export `tokens.css`"
    );
    assert!(
        Reason::MissingCodeMapping
            .line()
            .starts_with("missing code mapping")
    );
    assert_eq!(
        Reason::RedLint("STATE007 x".into()).line(),
        "red lint STATE007 x"
    );
}
