//! `rule new` scaffolding (frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W).

use gob_plan::check::compile_diagnostics;
use gob_plan::verbs::new::{NewError, parse_location, scaffold};

const SRC: &str = "fn parse() {\n    let n = 1;\n    dbg!(tokens.len());\n}\n";

// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
// frob:tests crates/gob-plan/src/verbs/new.rs::scaffold
#[test]
fn a_call_line_becomes_an_args_snippet_with_a_fire_example() {
    let r = scaffold("NOPE001", "src/parse.rs", 3, SRC).unwrap();
    assert_eq!(r.path, "rules/NOPE001.grl");
    assert_eq!(r.from, "dbg!(tokens.len())");
    assert!(r.text.contains("find d: `dbg!($$$ARGS)`"), "{}", r.text);
    assert!(
        r.text.contains("dbg!(tokens.len());        //~ error"),
        "{}",
        r.text
    );
    assert!(r.text.contains("## Remedy"));
}

// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
// frob:tests crates/gob-plan/src/verbs/new.rs::scaffold
#[test]
fn the_scaffold_fails_only_on_the_missing_clean_example() {
    for (file, src) in [("a.rs", SRC), ("a.py", "x = 1\nprint(x)\n")] {
        let line = if file == "a.rs" { 3 } else { 2 };
        let r = scaffold("NOPE001", file, line, src).unwrap();
        let diags = compile_diagnostics(&r.path, &r.text);
        let codes: Vec<_> = diags
            .iter()
            .filter_map(|d| d.code)
            .map(gob_plan::check::Code::as_str)
            .collect();
        assert_eq!(codes, ["GRL011"], "{file}\n{}", r.text);
        assert!(diags[0].message.contains("`clean`"), "{}", diags[0].message);
    }
}

// frob:ticket 01M3ZX7HCQYMTNB9S8ANCZA04W
// frob:tests crates/gob-plan/src/verbs/new.rs::scaffold
#[test]
fn bad_input_is_a_typed_error() {
    assert_eq!(parse_location("src/parse.rs:42"), Ok(("src/parse.rs", 42)));
    assert!(matches!(
        parse_location("src/parse.rs"),
        Err(NewError::BadLocation(_))
    ));
    assert!(matches!(
        parse_location("a.rs:0"),
        Err(NewError::BadLocation(_))
    ));
    assert!(matches!(
        scaffold("nope1", "a.rs", 1, SRC),
        Err(NewError::BadId(_))
    ));
    assert!(matches!(
        scaffold("NOPE001", "a.txt", 1, SRC),
        Err(NewError::UnknownLanguage(_))
    ));
    assert_eq!(
        scaffold("NOPE001", "a.rs", 9, SRC),
        Err(NewError::NoSuchLine { line: 9, lines: 4 })
    );
    assert_eq!(
        scaffold("NOPE001", "a.rs", 4, SRC),
        Err(NewError::NoCode(4))
    );
}
