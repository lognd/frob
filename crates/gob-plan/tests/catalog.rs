//! The relation catalog: kinds keyed on the capability matrix, typed side relations and the
//! config schema (grl-spec.md section 6).

use gob_caps::Lang;
use gob_plan::catalog::{self, ConfigSchema};
use gob_plan::check::{Code, check_file_with};
use gob_plan::grl::parse;
use gob_text::FileInterner;
use serde_json::{Value, json};

fn real_schema() -> Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../docs/schemas/config.json"
    );
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
}

/// The generated schema with the `$defs` entry the exporter should carry for `ForbidImport`.
fn schema_with_defs() -> Value {
    let mut doc = real_schema();
    doc["$defs"] = json!({"ForbidImport": {"type": "object", "properties": {
        "from": {"type": "string"}, "to": {"type": "string"}, "reason": {"type": "string"}
    }}});
    doc
}

fn rule(body: &str) -> String {
    format!(
        "rule NOPE999 \"t\" {{\n  lang rust\n{body}\n  example fire \"\"\"\n    x\n  \"\"\"\n  example clean \"\"\"\n    y\n  \"\"\"\n  explain \"\"\"\n    e\n\n    ## Remedy\n    r\n  \"\"\"\n}}\n"
    )
}

fn codes(schema: &ConfigSchema, body: &str) -> Vec<(Code, String)> {
    let src = rule(body);
    let parsed = parse(FileInterner::new().intern("t.grl"), &src);
    assert!(parsed.is_ok(), "{:?}\n{src}", parsed.errors);
    check_file_with(&parsed.file, Some(schema))
        .into_iter()
        .filter_map(|d| d.code.map(|c| (c, d.message)))
        .collect()
}

// frob:ticket 01M3ZX7DMYNTWB3AP04CDMAECH
// frob:tests crates/gob-plan/src/catalog/mod.rs::kind
// frob:tests crates/gob-plan/src/catalog/mod.rs::render
#[test]
fn every_kind_has_a_query_languages_and_unknown_flags() {
    for k in catalog::KINDS {
        assert!(!k.query.is_empty(), "{}", k.word);
        assert!(Lang::ALL.iter().any(|l| k.answered_by(*l)), "{}", k.word);
    }
    assert!(
        catalog::kind("attribute")
            .unwrap()
            .field("value")
            .unwrap()
            .may_be_unknown
    );
    assert!(catalog::render().contains("## Side relations"));
}

// frob:ticket 01M3ZX7DMYNTWB3AP04CDMAECH
// frob:tests crates/gob-plan/src/catalog/config.rs::ConfigSchema.from_json
// frob:tests crates/gob-plan/src/catalog/config.rs::ConfigSchema.node
#[test]
fn the_real_config_schema_types_tables_and_keys() {
    let s = ConfigSchema::from_json(&real_schema());
    assert!(s.tables().contains(&"invariants") && s.tables().contains(&"lease"));
    assert_eq!(
        s.node("lease.ttl_secs").unwrap().ty,
        catalog::FieldType::Int
    );
    assert!(s.node("lease.ttl_secz").is_none());
}

// frob:ticket 01M3ZX7DMYNTWB3AP04CDMAECH
// frob:tests crates/gob-plan/src/check/mod.rs::check_file_with
#[test]
fn a_misspelt_config_column_is_not_a_member() {
    let s = ConfigSchema::from_json(&schema_with_defs());
    let ok = "  find f: config.invariants.forbid_imports\n  report f \"x\" when f.from == f.to";
    assert!(codes(&s, ok).is_empty());
    let bad = "  find f: config.invariants.forbid_imports\n  report f \"x\" when f.frm == f.to";
    assert_eq!(
        codes(&s, bad),
        [(Code::Grl001, "unknown column `frm`".to_owned())]
    );
    let table = "  find f: config.invariant.forbid_imports\n  report f \"x\"";
    assert_eq!(codes(&s, table)[0].1, "unknown config key `invariant`");
}
