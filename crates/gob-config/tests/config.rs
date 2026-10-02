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
