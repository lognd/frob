//! Cycle 1 spellings carried in the planning AST (grmb-spec 11.1, 11.5, 12.5): fmt keeps each one.

// frob:ticket 01M6C52KX8TM6CC38XZDK583KA

use grimble_model::fmt::format_file;
use grimble_model::parse::parse_file;

const H: &str = "grimble = \"2\";\nmodule m;\n\n";

/// Formats `body` under the standard header and returns the printed body.
fn printed(body: &str) -> String {
    let src = format!("{H}{body}");
    let f = parse_file("m.grmb", src.as_bytes());
    assert_eq!(f.holes, 0, "{src}");
    let out = format_file(&f).expect("formats");
    let again = parse_file("m.grmb", out.as_bytes());
    assert_eq!(
        format_file(&again).expect("formats again"),
        out,
        "fmt is idempotent"
    );
    out[H.len()..].to_owned()
}

/// Asserts `body` is already in fmt's output form.
fn keeps(body: &str) {
    assert_eq!(printed(body), body);
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn use_and_include_keep_their_spelling() {
    keeps("use \"a.grmb\";\n");
    keeps("include \"a.grmb\";\n");
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn verified_by_and_evidence_tests_keep_their_spelling() {
    keeps("node n : trusted {\n  verified_by \"tests/t.rs\";\n}\n");
    keeps("node n : trusted {\n  evidence tests \"tests/t.rs\";\n}\n");
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn step_open_and_idempotent_round_trip() {
    keeps("step system.a : open { ok, no };\n");
    keeps("step system.a : { ok, no } idempotent;\n");
    keeps("step system.a : open { ok } idempotent;\n");
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn retry_within_and_omitted_step_round_trip() {
    let body =
        |chain: &str| format!("scenario s {{\n  system.a => {{\n    _ => {chain};\n  }}\n}}\n");
    for chain in [
        "retry system.a max 3 within 5 s",
        "retry max 3",
        "retry max 3 within 5 s else end ok",
    ] {
        keeps(&body(chain));
    }
}

#[test]
// frob:tests crates/grimble-model/src/fmt.rs::format_file
fn arm_arrow_spelling_round_trips() {
    let out =
        printed("scenario s {\n  system.a => {\n    ok -> end ok;\n    _ => end ok;\n  }\n}\n");
    assert!(out.contains("ok -> end ok;"), "{out}");
    assert!(out.contains("_  => end ok;"), "{out}");
}
