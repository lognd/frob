//! `crunk:waive` reading, binding and the exceptions it grants.

// frob:ticket 01M43ATASM383KB9130JY79XVV

use crunk_rules::waiver::{exceptions, scan};
use gob_rules::ExceptionKind;

// frob:tests crates/crunk-rules/src/waiver.rs::scan
#[test]
fn a_trailing_waiver_covers_its_own_line() {
    let text = ".a {\n  padding: 13px; /* crunk:waive SPACE001 reason=\"legacy embed\" */\n}\n";
    let w = scan(text);
    assert_eq!(w.len(), 1);
    assert_eq!((w[0].rule.as_str(), w[0].line), ("SPACE001", 2));
    assert_eq!(w[0].reason.as_deref(), Some("legacy embed"));
    let r = w[0].covers.clone().expect("region");
    assert!(text[r].contains("padding: 13px;"));
}

// frob:tests crates/crunk-rules/src/waiver.rs::scan
#[test]
fn a_leading_waiver_covers_the_next_declaration_up_to_its_semicolon() {
    let text = ".a {\n  /* crunk:waive SPACE001 reason=\"why\" */\n\n  padding: 13px;\n  margin: 7px;\n}\n";
    let r = scan(text)[0].covers.clone().expect("region");
    assert_eq!(text[r].trim(), "padding: 13px;");
}

// frob:tests crates/crunk-rules/src/waiver.rs::scan
#[test]
fn a_waiver_with_nothing_after_it_is_an_orphan() {
    let text = ".a { padding: 1px; }\n/* crunk:waive SPACE001 reason=\"why\" */\n";
    assert_eq!(scan(text)[0].covers, None);
}

// frob:tests crates/crunk-rules/src/waiver.rs::scan
#[test]
fn reasons_missing_blank_or_quoted_with_escapes_are_read() {
    let text = "/* crunk:waive A001 */\n// crunk:waive B002 reason=\"\"\n# crunk:waive C003 reason=\"say \\\"hi\\\"\"\n<!-- crunk:waive D004 reason=\"x\" -->\n";
    let w = scan(text);
    let got: Vec<_> = w
        .iter()
        .map(|w| (w.rule.as_str(), w.reason.as_deref()))
        .collect();
    assert_eq!(
        got,
        [
            ("A001", None),
            ("B002", None),
            ("C003", Some("say \"hi\"")),
            ("D004", Some("x"))
        ]
    );
}

// frob:tests crates/crunk-rules/src/waiver.rs::scan
#[test]
fn prose_and_malformed_comments_are_not_waivers() {
    for text in [
        "/* about crunk:waive here */",
        "/* crunk:waive */",
        "/* crunk:waiver X001 */",
        "const s = \"crunk:waive X001 reason=\\\"y\\\"\";",
        "/* crunk:waive X001 reason=\"never closes */",
    ] {
        assert!(scan(text).is_empty(), "{text}");
    }
}

// frob:tests crates/crunk-rules/src/waiver.rs::exceptions
#[test]
fn only_a_reasoned_waiver_of_a_waivable_rule_grants_an_exception() {
    let text = concat!(
        ".a {\n",
        "  color: red; /* crunk:waive COLOR001 reason=\"brand red\" */\n",
        "  color: blue; /* crunk:waive COLOR001 */\n",
        "  gap: 3px; /* crunk:waive ORG002 reason=\"nope\" */\n",
        "  gap: 5px; /* crunk:waive WAIVE001 reason=\"nope\" */\n",
        "}\n",
    );
    let ex = exceptions("a.css", text);
    assert_eq!(ex.len(), 1);
    assert_eq!(ex[0].exception.rule.as_str(), "COLOR001");
    assert_eq!(ex[0].exception.kind, ExceptionKind::Accept);
    assert_eq!(ex[0].exception.reason, "brand red");
    assert_eq!(ex[0].path, "a.css");
}
