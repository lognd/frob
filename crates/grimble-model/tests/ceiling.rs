//! `ceiling LEVEL forbids ATOM, ...;` parses, formats to a fixed point and rejects malformed forms.

// frob:ticket 01M5XNNJMSCGPFS84V3PZQKTNC

use grimble_model::ast::{Atom, FileStatus, Item};
use grimble_model::fmt::format_file;
use grimble_model::parse::parse_file;

const SRC: &str = "grimble = \"2\";\nmodule m;\n\nceiling  foreign forbids process.spawn,fs.write;\n\nnode a : foreign {\n  owns \"src/**\";\n}\n";

// frob:tests crates/grimble-model/src/parse.rs::parse_file
#[test]
fn ceiling_item_parses_level_and_atoms() {
    let f = parse_file("m.grmb", SRC.as_bytes());
    assert_eq!(f.status, FileStatus::Parsed);
    let c = f
        .items
        .iter()
        .find_map(|i| match i {
            Item::Ceiling(c) => Some(c),
            _ => None,
        })
        .expect("a ceiling item");
    assert_eq!(c.level.text, "foreign");
    let atoms: Vec<String> = c.forbids.iter().map(Atom::written).collect();
    assert_eq!(atoms, ["process.spawn", "fs.write"]);
}

// frob:tests crates/grimble-model/src/fmt.rs::format_file
#[test]
fn ceiling_item_formats_to_a_fixed_point() {
    let once = format_file(&parse_file("m.grmb", SRC.as_bytes())).expect("formats");
    assert!(
        once.contains("ceiling foreign forbids process.spawn, fs.write;"),
        "{once}"
    );
    let twice = format_file(&parse_file("m.grmb", once.as_bytes())).expect("formats");
    assert_eq!(once, twice);
}

// frob:tests crates/grimble-model/src/parse.rs::parse_file
#[test]
fn ceiling_without_forbids_is_a_hole() {
    let src = "grimble = \"2\";\nmodule m;\nceiling foreign fs.write;\n";
    let f = parse_file("m.grmb", src.as_bytes());
    assert!(f.is_damaged(), "{:?}", f.status);
}
