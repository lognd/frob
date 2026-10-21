//! Fuzz the crunk.toml loader: arbitrary text never panics.
// frob:ticket 01M47QV3BRRZZSMJ5Q79N8G5S2
#![no_main]

use std::path::Path;

use crunk_spec::parse_spec;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|text: &str| {
    let _ = parse_spec(text, Path::new("crunk.toml"), Path::new("."));
});
