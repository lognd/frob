//! Direct call to `Library::as_str`.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use gob_frameworks::Library;

// frob:tests crates/gob-frameworks/src/http.rs::Library.as_str
#[test]
fn libraries_spell_themselves_in_lowercase() {
    assert_eq!(Library::as_str(Library::Fetch), "fetch");
    assert_eq!(Library::as_str(Library::Axios), "axios");
}
