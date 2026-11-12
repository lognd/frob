//! `provides C via S` (grimble-capabilities-v3.md 5.3): it parses, formats and round-trips.

// frob:ticket 01M666NX8TN1R3X13Q4S9CTJ1V

use grimble_model::ast::{ClauseKind, Item};
use grimble_model::fmt::format_file;
use grimble_model::parse::parse_file;

const SRC: &str = "grimble = \"2\";\nmodule m;\n\nnode store : trusted {\n  owns \"src/store/**\";\n  provides fs.write(\"data/**\") via \"src/store/fs.rs::Store.put\" because=\"the one writer\";\n}\n";

/// The `provides` clauses found in the first node of `text`, as (atom, args, via text).
fn provides_of(text: &str) -> Vec<(String, Vec<String>, String)> {
    let parsed = parse_file("design/m.grmb", text.as_bytes());
    assert!(!parsed.is_damaged(), "{:?}", parsed.diags);
    let mut out = Vec::new();
    for item in &parsed.items {
        if let Item::Entity(e) = item {
            for c in &e.clauses {
                if let ClauseKind::Provides(p) = &c.kind {
                    out.push((
                        p.atom.written(),
                        p.args.iter().map(|a| a.value.clone()).collect(),
                        p.via.text.trim().to_owned(),
                    ));
                }
            }
        }
    }
    out
}

// frob:tests crates/grimble-model/src/parse.rs::parse_file
#[test]
fn provides_via_parses_atom_args_and_provider() {
    let got = provides_of(SRC);
    assert_eq!(
        got,
        vec![(
            "fs.write".to_owned(),
            vec!["data/**".to_owned()],
            "\"src/store/fs.rs::Store.put\"".to_owned()
        )]
    );
}

// frob:tests crates/grimble-model/src/fmt.rs::format_file
#[test]
fn provides_via_round_trips_through_the_formatter() {
    let parsed = parse_file("design/m.grmb", SRC.as_bytes());
    let once = format_file(&parsed).expect("formats");
    assert_eq!(provides_of(&once), provides_of(SRC));
    let again = format_file(&parse_file("design/m.grmb", once.as_bytes())).expect("formats");
    assert_eq!(once, again, "fmt is a fixed point");
}

// frob:tests crates/grimble-model/src/parse.rs::parse_file
#[test]
fn provides_without_via_is_a_parse_error() {
    let parsed = parse_file(
        "design/m.grmb",
        b"grimble = \"2\";\nmodule m;\nnode a : trusted {\n  provides fs.write;\n}\n",
    );
    assert!(parsed.is_damaged());
}
