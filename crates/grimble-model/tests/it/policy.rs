//! `policy NAME { ... }`, `use NAME;` and `until=`/`profile=` on `may` parse and format to a fixed point.

// frob:ticket 01M5XNNJTK08K3CB98MCT14W34

use grimble_model::ast::FileStatus;
use grimble_model::fmt::format_file;
use grimble_model::parse::parse_file;

const SRC: &str = "grimble = \"2\";\nmodule m;\n\npolicy io {\n  may fs.read at \"src/**\" until=2999-01-01 profile=test;\n}\n\nnode a : trusted {\n  owns \"src/**\";\n  use io;\n}\n";

// frob:tests crates/grimble-model/src/parse.rs::parse_file
#[test]
fn policy_and_use_parse_cleanly() {
    let f = parse_file("m.grmb", SRC.as_bytes());
    assert_eq!(f.status, FileStatus::Parsed, "{:?}", f.status);
}

// frob:tests crates/grimble-model/src/fmt.rs::format_file
#[test]
fn policy_and_use_format_to_a_fixed_point() {
    let once = format_file(&parse_file("m.grmb", SRC.as_bytes())).expect("formats");
    assert!(once.contains("use io;"), "{once}");
    assert!(once.contains("until=2999-01-01"), "{once}");
    let twice = format_file(&parse_file("m.grmb", once.as_bytes())).expect("formats");
    assert_eq!(once, twice);
}
