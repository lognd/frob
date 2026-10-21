//! Fuzz the GRL parser and printer: no panic, and the formatter reaches a fixed point.
// frob:ticket 01M47QV3BRRZZSMJ5Q79N8G5S2
#![no_main]

use gob_plan::grl::format_source;
use gob_text::FileInterner;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|text: &str| {
    let file = FileInterner::new().intern("fuzz.grl");
    if let Ok(once) = format_source(file, text) {
        let twice = format_source(file, &once).expect("formatted GRL must re-parse");
        assert_eq!(once, twice, "GRL formatting must be a fixed point");
    }
});
