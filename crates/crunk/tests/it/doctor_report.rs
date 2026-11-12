//! Direct tests of `doctor::report` (frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5).

// frob:tests crates/crunk/src/doctor.rs::report
#[test]
fn report_marks_a_repository_without_crunk_toml_absent() {
    let dir = tempfile::tempdir().expect("tempdir");
    let payload = crunk::doctor::report(dir.path());
    assert_eq!(payload.data.config.status, "absent");
    assert!(!payload.data.config.present);
    assert_eq!(
        payload.data.root,
        gob_path::Shown::of(dir.path()).as_str().to_owned()
    );
    assert_eq!(payload.data.version, env!("CARGO_PKG_VERSION"));
}
