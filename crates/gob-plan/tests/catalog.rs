//! The relation catalog: kinds keyed on the capability matrix, typed side relations and the
//! config schema (grl-spec.md section 6).

use gob_caps::Lang;
use gob_plan::catalog::{self, ConfigSchema};
use gob_plan::check::{Code, check_file_with};
use gob_plan::grl::parse;
use gob_text::FileInterner;
use serde_json::Value;

fn real_schema() -> Value {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../docs/schemas/config.json"
    );
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
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
// frob:tests crates/gob-plan/src/catalog/mod.rs::Kind.field
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
// frob:ticket 01M4M5CRRV5A6P5WHHVHXP981B
// frob:tests crates/gob-plan/src/check/mod.rs::check_file_with
// frob:tests crates/gob-plan/src/check/mod.rs::compile_diagnostics_with
// frob:tests crates/gob-plan/src/check/mod.rs::compile_report_with
#[test]
fn a_misspelt_config_column_is_not_a_member() {
    let s = ConfigSchema::from_json(&real_schema());
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

// frob:ticket 01M4M5CRRV5A6P5WHHVHXP981B
// frob:tests crates/gob-plan/src/check/mod.rs::compile_report_with
#[test]
fn the_shipped_config_schema_types_forbid_import_columns() {
    let s = ConfigSchema::from_json(&real_schema());
    let cols: Vec<String> = s
        .node("invariants.forbid_imports")
        .and_then(|n| n.columns.clone())
        .unwrap_or_default()
        .into_iter()
        .map(|c| c.name)
        .collect();
    assert!(
        cols.contains(&"from".to_owned()) && cols.contains(&"to".to_owned()),
        "{cols:?}"
    );
    let src =
        rule("  find f: config.invariants.forbid_imports\n  report f \"x\" when f.frm == f.to");
    let with = gob_plan::check::compile_report_with("t.grl", &src, Some(&s));
    assert!(with.contains("unknown column `frm`"), "{with}");
    let without = gob_plan::check::compile_report_with("t.grl", &src, None);
    assert!(!without.contains("unknown column"), "{without}");
}

fn crunk_schema() -> Value {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../docs/schemas/crunk.json");
    serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap()
}

// frob:ticket 01M54GWME19N64RRMBTCZSG7YJ
// frob:tests crates/gob-plan/src/catalog/config.rs::ConfigSchema.from_json
// frob:tests crates/gob-plan/src/catalog/config.rs::ConfigSchema.node
#[test]
fn the_crunk_schema_types_org_and_layers() {
    let s = ConfigSchema::from_json(&crunk_schema());
    assert!(s.tables().contains(&"org") && s.tables().contains(&"layers"));
    assert_eq!(
        s.node("org.class_case").unwrap().ty,
        catalog::FieldType::Str
    );
    assert_eq!(
        s.node("org.component_prefix").unwrap().ty,
        catalog::FieldType::Bool
    );
    assert_eq!(s.node("org.ignore").unwrap().ty, catalog::FieldType::Str);
    let cols = |p: &str| -> Vec<String> {
        s.node(p)
            .and_then(|n| n.columns.clone())
            .unwrap_or_default()
            .into_iter()
            .map(|c| format!("{}:{}", c.name, c.ty.name()))
            .collect()
    };
    assert_eq!(cols("org.buckets"), ["value:string"]);
    assert_eq!(cols("layers"), ["name:string", "value:int"]);
    let ok = "  find b: config.org.buckets\n  report b \"x\" when b.value == \"a\"";
    assert!(codes(&s, ok).is_empty());
    let bad = "  find l: config.layers\n  report l \"x\" when l.z == 1";
    assert_eq!(
        codes(&s, bad),
        [(Code::Grl001, "unknown column `z`".to_owned())]
    );
    assert!(s.node("org.bucket").is_none());
}
