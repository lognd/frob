//! Guards the crate docs against claiming terms are uncached.
// frob:ticket
use std::path::Path;

#[test]
fn lib_docs_do_not_claim_terms_are_uncached() {
    let src = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("src")
        .join("lib.rs");
    let text = std::fs::read_to_string(src).expect("lib.rs readable");
    assert!(
        !text.contains("Terms are not"),
        "stale uncached-terms claim"
    );
    assert!(text.contains("Folded terms"), "cached-terms note missing");
}
