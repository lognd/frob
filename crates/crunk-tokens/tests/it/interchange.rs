//! Round-trip and validation tests for the lossless DTCG interchange.

// frob:ticket 01M4CXQYFA9ACDVWF4R62C50FH

use crunk_tokens::interchange::{Document, DtcgError};
use serde_json::Value;

const FULL: &str = r##"{
  "$description": "demo",
  "color": {
    "$type": "color",
    "$extensions": {"org.example": {"k": [1, 2.0]}},
    "ink": {"$value": "#e6e8ef", "$description": "text"},
    "link": {"$value": "{color.ink}"},
    "brand": {"$root": {"$value": "#f00"}, "dark": {"$value": {"colorSpace": "srgb", "components": [0, 0, 0]}}}
  },
  "space": {
    "$type": "dimension",
    "s": {"$value": {"value": 4, "unit": "px"}},
    "m": {"$value": "16px"},
    "$deprecated": true
  },
  "n": {"$type": "number", "a": {"$value": 16}, "b": {"$value": 16.0}},
  "ease": {"$type": "cubicBezier", "out": {"$value": [0.1, 0.2, 0.3, 1]}},
  "font": {"$type": "fontFamily", "sans": {"$value": ["Inter", "sans-serif"]}},
  "type": {"body": {"$type": "typography", "$value": {"fontFamily": "{font.sans}", "fontSize": "{space.m}"}}},
  "shadow": {"card": {"$type": "shadow", "$value": [{"color": "{color.ink}", "offsetX": "1px"}], "vendor": 1}},
  "alias": {"x": {"$value": "{color.link}"}}
}"##;

fn round_trip(text: &str) -> Value {
    Document::parse(text).expect("parses").to_value()
}

// frob:tests Document.parse
// frob:tests Document.to_value
#[test]
fn interchange_round_trip_equals_input() {
    assert_eq!(
        round_trip(FULL),
        serde_json::from_str::<Value>(FULL).unwrap()
    );
}

// frob:tests Document.render
#[test]
fn interchange_render_is_stable() {
    let doc = Document::parse(FULL).unwrap();
    let again = Document::parse(&doc.render()).unwrap();
    assert_eq!(doc, again);
    assert!(doc.render().ends_with('\n'));
}

// frob:tests Document.resolved_type
#[test]
fn interchange_types_resolve_through_groups_and_aliases() {
    let doc = Document::parse(FULL).unwrap();
    assert_eq!(doc.resolved_type("color.ink").as_deref(), Some("color"));
    assert_eq!(doc.resolved_type("alias.x").as_deref(), Some("color"));
    assert_eq!(
        doc.resolved_type("type.body").as_deref(),
        Some("typography")
    );
    assert!(doc.token("color.brand.$root").is_some());
}

// frob:tests Document.summary
#[test]
fn interchange_summary_counts() {
    let s = Document::parse(FULL).unwrap().summary();
    assert_eq!(s.aliases, 2);
    assert_eq!(s.tokens, 13);
}

#[test]
fn interchange_number_forms_survive() {
    let text = r#"{"n": {"$type": "number", "a": {"$value": 16}, "b": {"$value": 16.5}}}"#;
    let out = round_trip(text);
    assert_eq!(out["n"]["a"]["$value"].to_string(), "16");
    assert_eq!(out["n"]["b"]["$value"].to_string(), "16.5");
}

#[test]
fn interchange_deep_nesting_round_trips() {
    let mut text = String::from(r#"{"$type": "number""#);
    for i in 0..60 {
        text.push_str(&[r#", ""#, &format!("g{i}"), r#"": {"$type": "number""#].concat());
    }
    text.push_str(r#", "t": {"$value": 1}"#);
    text.push_str(&"}".repeat(61));
    assert_eq!(
        round_trip(&text),
        serde_json::from_str::<Value>(&text).unwrap()
    );
}

#[test]
fn interchange_rejects_bad_input() {
    let err = |t: &str| Document::parse(t).unwrap_err();
    assert!(matches!(err("{nope"), DtcgError::Syntax { .. }));
    assert!(matches!(err("[]"), DtcgError::Invalid { .. }));
    assert!(
        err(r#"{"a": {"$value": 1, "$type": "number"}, "a": 2}"#)
            .to_string()
            .contains("duplicate")
    );
    assert!(matches!(
        err(r#"{"a": {"$value": 1}}"#),
        DtcgError::MissingType { .. }
    ));
    assert!(matches!(
        err(r#"{"a.b": {"$type": "number", "$value": 1}}"#),
        DtcgError::Invalid { .. }
    ));
    assert!(matches!(err(r#"{"a": 3}"#), DtcgError::Invalid { .. }));
    assert!(matches!(
        err(r#"{"a": {"$type": "number", "$value": "x"}}"#),
        DtcgError::Invalid { .. }
    ));
    assert!(matches!(
        err(r#"{"a": {"$type": "color", "$value": "{nope}"}}"#),
        DtcgError::BrokenReference { .. }
    ));
}

#[test]
fn interchange_rejects_reference_cycle() {
    let text = r#"{"a": {"$value": "{b}"}, "b": {"$value": "{a}"}}"#;
    assert!(matches!(
        Document::parse(text).unwrap_err(),
        DtcgError::Cycle { .. }
    ));
}

// frob:tests crates/crunk-tokens/src/interchange.rs::check_css_names
#[test]
fn colliding_css_names_are_refused() {
    let text = r##"{"a": {"$type": "color", "b-c": {"$value": "#fff"}}, "a-b": {"$type": "color", "c": {"$value": "#000"}}}"##;
    let err = Document::parse(text).expect_err("collision");
    assert_eq!(
        err,
        DtcgError::NameCollision {
            first: "a.b-c".into(),
            second: "a-b.c".into(),
            property: "--a-b-c".into(),
        }
    );
}

// frob:tests crates/crunk-tokens/src/interchange.rs::compile
#[test]
fn compile_returns_every_token_with_resolved_values() {
    let doc = Document::parse(FULL).expect("parses");
    let set = doc.compile().expect("compiles");
    assert_eq!(set.len(), doc.tokens().len());
    let ink = set.get("--color-ink").expect("ink");
    let alias = set.get("--color-link").expect("link");
    assert_eq!(ink.value, alias.value, "the alias resolves to its target");
    assert_eq!(set.get("--alias-x").expect("x").value, ink.value);
    assert_eq!(
        set.get("--space-m").expect("m").value.css().as_deref(),
        Some("16px")
    );
    assert!(set.get("--color-brand").is_some(), "$root names the group");
}

// frob:tests crates/crunk-tokens/src/interchange.rs::compile
#[test]
fn compile_refuses_a_type_the_model_cannot_hold() {
    let doc =
        Document::parse(r#"{"g": {"$type": "gradient", "a": {"$value": []}}}"#).expect("parses");
    assert!(matches!(doc.compile(), Err(DtcgError::Unsupported { .. })));
}

const POINTER_DOC: &str = r##"{
  "color": {"$type": "color", "ink": {"$value": "#e6e8ef"}, "link": {"$value": {"$ref": "#/color/ink/$value"}}},
  "a~b": {"c/d": {"$type": "number", "$value": 7}},
  "esc": {"$type": "number", "$value": {"$ref": "#/a~0b/c~1d/$value"}}
}"##;

fn by_key(set: &crunk_tokens::TokenSet, key: &str) -> crunk_tokens::TokenValue {
    set.iter().find(|t| t.key == key).expect(key).value.clone()
}

// frob:tests crates/crunk-tokens/src/interchange.rs::compile
#[test]
fn compile_resolves_ref_json_pointer() {
    let set = Document::parse(POINTER_DOC)
        .expect("parses")
        .compile()
        .expect("compiles");
    assert_eq!(by_key(&set, "color.link"), by_key(&set, "color.ink"));
    assert_eq!(by_key(&set, "esc"), by_key(&set, "a~b.c/d"));
}

// frob:tests crates/crunk-tokens/src/interchange.rs::compile
#[test]
fn compile_refuses_unresolvable_ref_pointer() {
    let text = r##"{"n": {"$type": "number", "$value": {"$ref": "#/missing/token/$value"}}}"##;
    let err = Document::parse(text).expect_err("refused");
    assert!(
        matches!(&err, DtcgError::BrokenReference { target, .. } if target == "#/missing/token/$value"),
        "{err}"
    );
}

// frob:tests crates/crunk-tokens/src/interchange.rs::compile
#[test]
fn compile_refuses_cyclic_ref_pointer() {
    let text = r##"{"a": {"$type": "number", "$value": {"$ref": "#/b/$value"}}, "b": {"$value": {"$ref": "#/a/$value"}}}"##;
    let err = Document::parse(text)
        .and_then(|d| d.compile().map(|_| ()))
        .expect_err("refused");
    assert!(err.to_string().contains("cyclic"), "{err}");
}
