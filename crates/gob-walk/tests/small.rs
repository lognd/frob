//! Digest bytes and three-valued lifting in gob-walk.
// frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

use gob_walk::Digest;
use gob_walk::selector::Tri;

// frob:tests crates/gob-walk/src/lib.rs::Digest.as_bytes
#[test]
fn digest_bytes_are_the_blake3_of_the_input() {
    let d = Digest::of(b"abc");
    assert_eq!(d.as_bytes(), blake3::hash(b"abc").as_bytes());
    assert_ne!(d, Digest::of(b"xyz"));
}

// frob:tests crates/gob-walk/src/selector/mod.rs::Tri.from_bool
#[test]
fn tri_lifts_booleans() {
    assert_eq!(Tri::from_bool(true), Tri::Yes);
    assert_eq!(Tri::from_bool(false), Tri::No);
}
