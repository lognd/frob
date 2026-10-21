//! Behavior tests for gob-config: load, materialize, check, schema.

use std::collections::BTreeMap;

use gob_config::{
    ConfigError, ConfigSource, ConfigTable, Provenance, TableDescription, all_tables, check, load,
    load_with, materialize, schema,
};

/// Ticket settings.
#[derive(Debug, ConfigTable)]
#[config(table = "tickets", materialize)]
struct Tickets {
    /// Compare-and-swap retries when updating the ledger.
    #[config(default = 5, enforcement)]
    cas_retries: u32,
    /// Where tickets live: `trunk` or `branch`.
    #[config(default = "trunk".to_owned(), enforcement)]
    r#ref: String,
    /// Free-form labels.
    #[config(default = Vec::new())]
    labels: Vec<String>,
}

/// Lease settings.
#[derive(Debug, ConfigTable)]
#[config(table = "tickets.lease", materialize)]
struct Lease {
    /// Minutes before a lease expires.
    #[config(default = 120, enforcement)]
    ttl_minutes: u64,
}

fn descs() -> (TableDescription, TableDescription) {
    (Tickets::describe(), Lease::describe())
}

fn write(dir: &tempfile::TempDir, text: &str) {
    std::fs::write(dir.path().join("frob.toml"), text).unwrap();
}

#[test]
fn defaults_when_file_absent() {
    let dir = tempfile::tempdir().unwrap();
    let loaded = load::<Tickets>(dir.path(), "frob").unwrap();
    assert!(!loaded.file_present);
    assert_eq!(loaded.value.cas_retries, 5);
    assert_eq!(loaded.value.r#ref, "trunk");
    assert!(loaded.value.labels.is_empty());
    assert_eq!(loaded.provenance["cas_retries"], Provenance::Default);
    insta::assert_debug_snapshot!(loaded.value);
}

#[test]
fn file_beats_default_and_override_beats_file() {
    let dir = tempfile::tempdir().unwrap();
    write(&dir, "[tickets]\ncas_retries = 9\nref = \"branch\"\n");
    let loaded = load::<Tickets>(dir.path(), "frob").unwrap();
    assert_eq!(loaded.value.cas_retries, 9);
    assert_eq!(loaded.provenance["cas_retries"], Provenance::File);

    let mut source = ConfigSource::new(dir.path(), "frob");
    source
        .overrides
        .insert("tickets.cas_retries".to_owned(), toml::Value::Integer(11));
    let loaded = load_with::<Tickets>(&source).unwrap();
    assert_eq!(loaded.value.cas_retries, 11);
    assert_eq!(loaded.value.r#ref, "branch");
    assert_eq!(loaded.provenance["cas_retries"], Provenance::Override);
    assert_eq!(loaded.provenance["ref"], Provenance::File);
    assert_eq!(loaded.provenance["labels"], Provenance::Default);
}

#[test]
fn unknown_key_suggests_nearest() {
    let dir = tempfile::tempdir().unwrap();
    write(&dir, "[tickets]\ncas_retrys = 3\n");
    let err = load::<Tickets>(dir.path(), "frob").unwrap_err();
    assert!(matches!(
        &err,
        ConfigError::UnknownKey { key, suggestion: Some(s), .. }
            if key == "cas_retrys" && s == "cas_retries"
    ));
    insta::assert_snapshot!(err.to_string());
}

#[test]
fn unknown_key_without_close_match_has_no_suggestion() {
    let dir = tempfile::tempdir().unwrap();
    write(&dir, "[tickets]\nzzzzzzzzzzzz = 3\n");
    let err = load::<Tickets>(dir.path(), "frob").unwrap_err();
    assert!(matches!(
        err,
        ConfigError::UnknownKey {
            suggestion: None,
            ..
        }
    ));
}

#[test]
fn wrong_type_is_invalid() {
    let dir = tempfile::tempdir().unwrap();
    write(&dir, "[tickets]\ncas_retries = \"many\"\n");
    assert!(matches!(
        load::<Tickets>(dir.path(), "frob"),
        Err(ConfigError::Invalid { .. })
    ));
}

#[test]
fn nested_table_loads() {
    let dir = tempfile::tempdir().unwrap();
    write(&dir, "[tickets.lease]\nttl_minutes = 30\n");
    assert_eq!(
        load::<Lease>(dir.path(), "frob").unwrap().value.ttl_minutes,
        30
    );
    assert_eq!(
        load::<Tickets>(dir.path(), "frob")
            .unwrap()
            .value
            .cas_retries,
        5
    );
}

#[test]
fn materialize_preserves_comments_and_order() {
    let dir = tempfile::tempdir().unwrap();
    write(
        &dir,
        "# project config\n[zeta]\nkeep = true # trailing\n\n[tickets]\n# my own note\nref = \"branch\"\n",
    );
    let (t, l) = descs();
    let report = materialize(dir.path(), "frob", &[&t, &l]).unwrap();
    assert_eq!(
        report.added,
        ["tickets.cas_retries", "tickets.lease.ttl_minutes"]
    );
    assert!(!report.created);
    let text = std::fs::read_to_string(dir.path().join("frob.toml")).unwrap();
    insta::assert_snapshot!(text);

    // Idempotent: a second run adds nothing and leaves bytes alone.
    let again = materialize(dir.path(), "frob", &[&t, &l]).unwrap();
    assert!(again.added.is_empty());
    assert_eq!(
        std::fs::read_to_string(dir.path().join("frob.toml")).unwrap(),
        text
    );
    assert!(check(dir.path(), "frob", &[&t, &l]).unwrap().is_empty());
    // The result still loads.
    assert_eq!(
        load::<Tickets>(dir.path(), "frob").unwrap().value.r#ref,
        "branch"
    );
}

#[test]
fn materialize_creates_absent_file() {
    let dir = tempfile::tempdir().unwrap();
    let (t, l) = descs();
    let report = materialize(dir.path(), "frob", &[&t, &l]).unwrap();
    assert!(report.created);
    insta::assert_snapshot!(std::fs::read_to_string(dir.path().join("frob.toml")).unwrap());
}

#[test]
fn check_emits_cfg001_per_missing_knob() {
    let dir = tempfile::tempdir().unwrap();
    write(&dir, "[tickets]\ncas_retries = 5\n");
    let (t, l) = descs();
    let findings = check(dir.path(), "frob", &[&t, &l]).unwrap();
    let messages: Vec<&str> = findings.iter().map(|f| f.message.as_str()).collect();
    insta::assert_debug_snapshot!(messages);
    assert!(findings.iter().all(|f| f.rule.as_str() == "CFG001"));
}

#[test]
fn check_on_absent_file_flags_everything() {
    let dir = tempfile::tempdir().unwrap();
    let (t, l) = descs();
    assert_eq!(check(dir.path(), "frob", &[&t, &l]).unwrap().len(), 3);
}

#[test]
fn schema_has_property_per_table() {
    let (t, l) = descs();
    insta::assert_json_snapshot!(schema(&[&t, &l]));
}

#[test]
fn inventory_lists_derived_tables() {
    let names: BTreeMap<String, bool> = all_tables().map(|d| (d.table, d.materialize)).collect();
    assert_eq!(names.get("tickets"), Some(&true));
    assert_eq!(names.get("tickets.lease"), Some(&true));
}

#[test]
fn describe_carries_docs_and_defaults() {
    insta::assert_debug_snapshot!(Tickets::describe());
}

/// One row of a table-valued knob.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, schemars::JsonSchema)]
struct Row {
    /// Source module.
    from: String,
    /// Target module.
    to: u32,
}

/// A self-referential definition.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, schemars::JsonSchema)]
struct Node {
    /// Child nodes.
    children: Vec<Node>,
}

/// Table with row-typed knobs.
#[derive(Debug, ConfigTable)]
#[config(table = "rows")]
struct Rows {
    /// Rows.
    #[config(default = Vec::new())]
    list: Vec<Row>,
    /// A tree.
    #[config(default = Vec::new())]
    tree: Vec<Node>,
}

/// More row-typed knobs, sharing the `Row` definition with `Rows`.
#[derive(Debug, ConfigTable)]
#[config(table = "rows.more")]
struct MoreRows {
    /// Rows again.
    #[config(default = Vec::new())]
    list: Vec<Row>,
}

/// Every `#/$defs/NAME` link under `node`.
fn refs_in(node: &serde_json::Value, out: &mut Vec<String>) {
    match node {
        serde_json::Value::Object(m) => {
            if let Some(r) = m.get("$ref").and_then(|r| r.as_str()) {
                out.push(r.to_owned());
            }
            m.values().for_each(|v| refs_in(v, out));
        }
        serde_json::Value::Array(a) => a.iter().for_each(|v| refs_in(v, out)),
        _ => {}
    }
}

fn row_schema() -> serde_json::Value {
    let (r, m) = (Rows::describe(), MoreRows::describe());
    let (dr, dm) = (Rows::default(), MoreRows::default());
    assert!(dr.list.is_empty() && dr.tree.is_empty() && dm.list.is_empty());
    schema(&[&r, &m])
}

#[test]
fn schema_ref_links_resolve_to_defs() {
    let doc = row_schema();
    let mut refs = Vec::new();
    refs_in(&doc, &mut refs);
    assert!(refs.len() >= 3, "{refs:?}");
    for r in refs {
        let target = r.strip_prefix('#').and_then(|p| doc.pointer(p));
        assert!(target.is_some(), "dangling {r}");
    }
}

#[test]
fn schema_types_row_columns() {
    let doc = row_schema();
    let props = &doc["$defs"]["Row"]["properties"];
    assert_eq!(props["from"]["type"], "string");
    assert_eq!(props["to"]["type"], "integer");
    assert_eq!(
        doc["properties"]["rows"]["properties"]["list"]["items"]["$ref"],
        "#/$defs/Row"
    );
}

#[test]
fn schema_defs_merge_once_and_allow_recursion() {
    let doc = row_schema();
    let defs = doc["$defs"].as_object().unwrap();
    assert_eq!(defs.len(), 2, "{:?}", defs.keys().collect::<Vec<_>>());
    assert_eq!(
        defs["Node"]["properties"]["children"]["items"]["$ref"],
        "#/$defs/Node"
    );
    let field = &doc["properties"]["rows"]["properties"]["list"];
    assert!(
        field.get("$defs").is_none(),
        "carried defs must be lifted: {field}"
    );
}

#[test]
fn schema_without_refs_has_no_defs() {
    let (t, l) = descs();
    assert!(schema(&[&t, &l]).get("$defs").is_none());
}

#[test]
fn shipped_schema_types_forbid_import_columns() {
    let path = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../docs/schemas/config.json"
    );
    let doc: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    let mut refs = Vec::new();
    refs_in(&doc, &mut refs);
    assert!(refs.iter().any(|r| r == "#/$defs/ForbidImport"));
    for r in &refs {
        assert!(
            doc.pointer(r.strip_prefix('#').unwrap()).is_some(),
            "dangling {r}"
        );
    }
    let cols = doc["$defs"]["ForbidImport"]["properties"]
        .as_object()
        .unwrap();
    assert!(!cols.is_empty());
}
