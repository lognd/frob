//! Serde behaviour of `RelPath`: plain-string round trip and validation on read.
#![allow(missing_docs)]

// frob:tests crates/gob-path/src/relpath.rs::RelPath
/// Given a `RelPath`, when serialized and read back, then it round-trips as a plain string and invalid input is refused.
#[test]
fn relpath_serde_round_trips_and_validates() {
    let p = gob_path::RelPath::new("a/b.rs").unwrap();
    let json = serde_json::to_string(&p).unwrap();
    assert_eq!(json, "\"a/b.rs\"");
    assert_eq!(serde_json::from_str::<gob_path::RelPath>(&json).unwrap(), p);
    assert!(serde_json::from_str::<gob_path::RelPath>("\"../x\"").is_err());
}
