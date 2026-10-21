//! Fuzz the .grmb parser and formatter: parsing is total, and formatted output re-formats to itself.
// frob:ticket 01M47QV3BRRZZSMJ5Q79N8G5S2
#![no_main]

use grimble_model::format_file;
use grimble_model::parse::parse_file;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|bytes: &[u8]| {
    let parsed = parse_file("fuzz.grmb", bytes);
    if let Ok(once) = format_file(&parsed) {
        let reparsed = parse_file("fuzz.grmb", once.as_bytes());
        let twice = format_file(&reparsed).expect("formatted .grmb must re-format");
        assert_eq!(once, twice, ".grmb formatting must be a fixed point");
    }
});
