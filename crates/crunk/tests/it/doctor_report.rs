//! Direct tests of `doctor::report` (frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5).

// frob:tests crates/crunk/src/doctor.rs::report
#[allow(
    clippy::disallowed_methods,
    reason = "the payload root is compared as the text the doctor reports"
)]
#[test]
fn report_marks_a_repository_without_crunk_toml_absent() {
    let dir = tempfile::tempdir().expect("tempdir");
    let payload = crunk::doctor::report(dir.path());
    assert_eq!(payload.data.config.status, "absent");
    assert!(!payload.data.config.present);
    assert_eq!(payload.data.root, dir.path().display().to_string());
    assert_eq!(payload.data.version, env!("CARGO_PKG_VERSION"));
}

// frob:tests crates/crunk/src/doctor.rs::report
#[test]
fn report_prints_the_tailwind_presence_table() {
    let dir = tempfile::tempdir().expect("tempdir");
    let payload = crunk::doctor::report(dir.path());
    let items: Vec<&str> = payload
        .data
        .tailwind
        .rows
        .iter()
        .map(|r| r.item.as_str())
        .collect();
    assert_eq!(items, ["node", "tailwindcss", "helper"]);
}
